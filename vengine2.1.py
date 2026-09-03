"""
vengine_02.py
Threaded, chunk-based speech capture + recognition pipeline for voice_engine.

Pipeline (3 threads, connected by queues so none of them block each other):

    [audio callback] --frame_queue--> [segmenter thread] --utterance_queue--> [transcriber thread] --> text

WHY THESE SPECIFIC COMPONENTS (this is the "industry level" pass)
-------------------------------------------------------------------
1. VAD: Silero VAD instead of a fixed RMS/energy threshold.
   A loudness threshold can't tell speech apart from a fan, a keyboard, or
   traffic outside -- it only knows "loud" vs "quiet". Silero VAD is a
   ~1-2MB neural model (the same class of model used in production
   dictation/call-center endpointing) that classifies actual speech
   spectral patterns, frame by frame, in real time on CPU. It plugs into
   this pipeline as a drop-in `is_speech(frame) -> bool` function, so the
   threading/segmentation logic underneath doesn't change at all.
   Falls back to calibrated RMS thresholding if Silero can't be loaded
   (e.g. no network on first run to fetch it via torch.hub), so the
   script still runs -- just less robustly in noisy rooms.

2. ASR: faster-whisper instead of openai-whisper.
   Same Whisper weights, a CTranslate2 backend that's ~4x faster on CPU.
   That speed headroom is spent on a *bigger, more accurate* model
   ("small" instead of "base") for the same latency budget, and it
   surfaces per-segment confidence stats (avg_logprob, no_speech_prob,
   compression_ratio) that openai-whisper's simple .transcribe() dict
   API doesn't expose as conveniently.

3. Hallucination guards: Whisper has a well-known failure mode where
   near-silent or noisy audio gets "transcribed" as fluent, plausible,
   completely made-up text (classic example: "Thank you for watching!"
   on dead air). The three thresholds below are OpenAI's own published
   defaults for catching this: reject a segment if its avg log-probability
   is too low, if it's a repetition loop (compression ratio too high), or
   if the model itself thinks it's silence (no_speech_prob too high).

4. condition_on_previous_text=False: each utterance here is an
   independent command, not one continuous recording. Leaving this on
   (the library default) lets Whisper drag context from a previous,
   unrelated utterance into the current one -- a known source of
   streaming-mode hallucination drift.

5. Explicit `language`: Whisper's language auto-detection only looks at
   the first ~30s of audio, and on a 1-3 second command it's unreliable --
   short clips get misdetected and decoded in the wrong language, which
   silently wrecks accuracy. Set LANGUAGE to what you're actually
   speaking; leave it None only if you genuinely need auto-detect and can
   accept that trade-off.

Design note: sounddevice/torch/faster-whisper are imported lazily inside
the functions that use them, not at module load time, so segmenter() --
the actual chunking/threading algorithm -- stays unit-testable with a
fake is_speech_fn and no heavy ML dependencies installed. See
test_segmenter.py.
"""

import queue
import threading
from collections import deque

import numpy as np

# ---------------------------------------------------------------- config --
SAMPLE_RATE = 16000                       # Hz -- what both Silero VAD and Whisper expect
FRAME_SAMPLES = 512                       # Silero VAD's *required* chunk size at 16kHz --
FRAME_MS = FRAME_SAMPLES / SAMPLE_RATE * 1000   # not a free choice; = 32ms

SILENCE_MS = 600                                    # continuous silence -> utterance ends
SILENCE_FRAMES = round(SILENCE_MS / FRAME_MS)

MIN_SPEECH_MS = 200                                 # ignore blips/clicks shorter than this
MIN_SPEECH_FRAMES = round(MIN_SPEECH_MS / FRAME_MS)

PRE_ROLL_MS = 300                                   # audio kept from BEFORE speech is
PRE_ROLL_FRAMES = round(PRE_ROLL_MS / FRAME_MS)     # detected, so the first syllable isn't clipped

MAX_UTTERANCE_S = 12                                # safety cap on one utterance's length

CALIBRATION_S = 0.5             # ambient noise sample duration (RMS fallback path only)
RMS_THRESHOLD_MULT = 3.0        # RMS fallback: speech = this many x louder than ambient
RMS_MIN_THRESHOLD = 0.01        # RMS fallback: floor

VAD_ENTER_THRESHOLD = 0.6       # Silero: probability needed to START counting as speech
VAD_EXIT_THRESHOLD = 0.35       # Silero: probability must drop below this to STOP --
                                 # the gap between enter/exit is hysteresis, so one noisy
                                 # frame near the boundary can't flicker the decision

LANGUAGE = "en"                 # set explicitly -- see note 5 above. None = auto-detect
ASR_MODEL_SIZE = "small"        # "base" also works; "small" is the accuracy upgrade
ASR_COMPUTE_TYPE = "int8"       # CPU-friendly quantization, negligible accuracy cost


def frame_rms(frame: np.ndarray) -> float:
    """Root-mean-square energy of one audio frame -- used only by the RMS fallback VAD."""
    return float(np.sqrt(np.mean(np.square(frame))))


# --------------------------------------------------------- pure pipeline --
# Deliberately independent of sounddevice/torch/whisper so it's unit-testable.

def segmenter(frame_source, utterance_sink, is_speech_fn, stop_event):
    """
    Consumes ~32ms raw frames from frame_source (anything with a .get()),
    groups them into utterances using is_speech_fn(frame) -> bool, and
    pushes each finished utterance -- one concatenated float32 np.array --
    onto utterance_sink. A None frame is treated as a shutdown signal.

    is_speech_fn is swappable: pass the Silero-backed one from build_vad()
    for real use, or any fake bool-returning function in tests.
    """
    pre_roll = deque(maxlen=PRE_ROLL_FRAMES)
    buffer = []
    speech_frames = 0
    silence_frames = 0
    state = "IDLE"

    while not stop_event.is_set():
        frame = frame_source.get()
        if frame is None:
            break

        is_speech = is_speech_fn(frame)

        if state == "IDLE":
            pre_roll.append(frame)
            if is_speech:
                state = "RECORDING"
                buffer = list(pre_roll)
                speech_frames = 1
                silence_frames = 0
        else:  # RECORDING
            buffer.append(frame)
            if is_speech:
                speech_frames += 1
                silence_frames = 0
            else:
                silence_frames += 1

            timed_out = len(buffer) * FRAME_MS >= MAX_UTTERANCE_S * 1000
            gone_quiet = silence_frames >= SILENCE_FRAMES

            if timed_out or gone_quiet:
                if speech_frames >= MIN_SPEECH_FRAMES:
                    utterance_sink.put(np.concatenate(buffer))
                state = "IDLE"
                buffer = []
                pre_roll.clear()


def transcribe_utterance(model, audio: np.ndarray, language=LANGUAGE) -> str:
    """
    Runs faster-whisper ONCE on a complete utterance and applies the
    hallucination guards described at the top of this file.
    """
    segments, _info = model.transcribe(
        audio,
        language=language,
        beam_size=5,
        best_of=5,
        condition_on_previous_text=False,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.6,
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text.lower()


def transcriber(utterance_source, text_sink, model, stop_event):
    """Consumes complete utterance buffers, transcribes each one exactly once."""
    while not stop_event.is_set():
        audio = utterance_source.get()
        if audio is None:
            break
        audio = audio.astype(np.float32)
        try:
            text = transcribe_utterance(model, audio)
        except Exception as e:
            text = ""
            print(f"[transcriber] error: {e}")
        if text:
            text_sink.put(text)


# ------------------------------------------------------------- live I/O --

def make_audio_callback(frame_queue):
    def callback(indata, frames, time_info, status):
        if status:
            print(status)
        frame_queue.put(indata[:, 0].copy())
    return callback


def calibrate_rms_threshold():
    """Fallback path only -- used when Silero VAD can't be loaded."""
    import sounddevice as sd
    print(f"Calibrating microphone -- stay quiet for {CALIBRATION_S}s...")
    samples = sd.rec(int(CALIBRATION_S * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                      channels=1, dtype='float32')
    sd.wait()
    ambient_rms = frame_rms(samples.flatten())
    threshold = max(ambient_rms * RMS_THRESHOLD_MULT, RMS_MIN_THRESHOLD)
    print(f"Ambient RMS: {ambient_rms:.5f} -> threshold: {threshold:.5f}")
    return threshold


def build_vad():
    """
    Returns a callable is_speech(frame) -> bool.
    Tries Silero VAD first (see module docstring for why); falls back to
    calibrated RMS thresholding if that fails for any reason.
    """
    try:
        import torch
        model, _utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad", model="silero_vad", trust_repo=True
        )
        state = {"active": False}

        def is_speech(frame: np.ndarray) -> bool:
            with torch.no_grad():
                prob = model(torch.from_numpy(frame), SAMPLE_RATE).item()
            if state["active"]:
                state["active"] = prob > VAD_EXIT_THRESHOLD
            else:
                state["active"] = prob > VAD_ENTER_THRESHOLD
            return state["active"]

        print("VAD: Silero (neural)")
        return is_speech

    except Exception as e:
        print(f"Silero VAD unavailable ({e}); falling back to RMS thresholding.")
        threshold = calibrate_rms_threshold()

        def is_speech(frame: np.ndarray) -> bool:
            return frame_rms(frame) > threshold

        print("VAD: RMS energy (fallback)")
        return is_speech


def build_asr_model():
    from faster_whisper import WhisperModel
    print(f"Loading faster-whisper '{ASR_MODEL_SIZE}' ({ASR_COMPUTE_TYPE})...")
    return WhisperModel(ASR_MODEL_SIZE, device="cpu", compute_type=ASR_COMPUTE_TYPE)


def main():
    import sounddevice as sd

    is_speech = build_vad()
    asr_model = build_asr_model()

    frame_queue = queue.Queue()
    utterance_queue = queue.Queue()
    text_queue = queue.Queue()
    stop_event = threading.Event()

    seg_thread = threading.Thread(
        target=segmenter, args=(frame_queue, utterance_queue, is_speech, stop_event), daemon=True)
    trans_thread = threading.Thread(
        target=transcriber, args=(utterance_queue, text_queue, asr_model, stop_event), daemon=True)
    seg_thread.start()
    trans_thread.start()

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=FRAME_SAMPLES,
        channels=1,
        dtype='float32',
        callback=make_audio_callback(frame_queue),
    )

    print("Listening... Ctrl+C to stop.")
    with stream:
        try:
            while True:
                text = text_queue.get()  # blocks until one full utterance is transcribed
                print("You said:", text)
                # hand off to your existing process_commands(text) here
        except KeyboardInterrupt:
            pass
        finally:
            stop_event.set()
            frame_queue.put(None)
            utterance_queue.put(None)


if __name__ == "__main__":
    main()