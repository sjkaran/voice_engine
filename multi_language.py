from transformers import pipeline
import sounddevice as sd
import numpy as np

# Load a community fine-tuned Odia Whisper model
from transformers import pipeline

pipe = pipeline("automatic-speech-recognition", model="Ranjit/odia_whisper_small_v3.0")

def record_and_transcribe(duration=5, sample_rate=16000):
    print("🎤 Recording...")
    audio = sd.rec(int(duration * sample_rate),
                   samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()
    audio = audio.flatten()

    result = pipe({"raw": audio, "sampling_rate": sample_rate})
    print(f"📝 Odia: {result['text']}")
    return result["text"]

record_and_transcribe()