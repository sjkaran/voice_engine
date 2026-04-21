import torch
import numpy as np
import sounddevice as sd
from transformers import AutoModelForCTC, AutoProcessor, VitsModel, AutoTokenizer

with open("API_KEY.txt","r")as key:
    HF_TOKEN = key.readline()

# Model IDs
STT_ID = "ai4bharat/indicwav2vec-odia"
TTS_ID = "facebook/mms-tts-ory"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def load_engines():
    print(f"🚀 Initializing AI Engines on {DEVICE}...")
    # STT Setup
    stt_proc = AutoProcessor.from_pretrained(STT_ID, token=HF_TOKEN)
    stt_model = AutoModelForCTC.from_pretrained(STT_ID, token=HF_TOKEN).to(DEVICE)
    
    # TTS Setup
    tts_tok = AutoTokenizer.from_pretrained(TTS_ID, token=HF_TOKEN)
    tts_model = VitsModel.from_pretrained(TTS_ID, token=HF_TOKEN).to(DEVICE)
    
    return stt_proc, stt_model, tts_tok, tts_model

def record_audio(duration=5, fs=16000):
    """Records audio from the microphone."""
    print(f"\n🎤 RECORDING ({duration}s)... Speak now in Odia!")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()  # Wait until recording is finished
    print("🛑 Recording Stopped.")
    return np.squeeze(recording)

def process_and_speak(audio_np, stt_proc, stt_model, tts_tok, tts_model):
    # 1. Normalize recording (Boosts low volume)
    audio_np = audio_np / (np.max(np.abs(audio_np)) + 1e-9)

    # 2. STT: Recognize
    inputs = stt_proc(audio_np, sampling_rate=16000, return_tensors="pt").input_values.to(DEVICE)
    with torch.no_grad():
        logits = stt_model(inputs).logits
    pred_ids = torch.argmax(logits, dim=-1)
    text = stt_proc.batch_decode(pred_ids, skip_special_tokens=True)[0]
    
    if not text.strip():
        print("⚠️ I didn't hear anything clearly.")
        return

    print(f"👂 Recognized: {text}")

    # 3. TTS: Speak Back
    print("🗣️ Generating Odia Voice...")
    tts_inputs = tts_tok(text, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        output_audio = tts_model(**tts_inputs).waveform[0].cpu().numpy()

    # 4. Playback
    sd.play(output_audio, samplerate=tts_model.config.sampling_rate)
    sd.wait()

# --- MAIN EXECUTION LOOP ---
if __name__ == "__main__":
    try:
        s_proc, s_model, t_tok, t_model = load_engines()
        
        while True:
            # Step 1: Record
            user_audio = record_audio(duration=5) # Adjust duration as needed
            
            # Step 2 & 3: Recognize & Speak
            process_and_speak(user_audio, s_proc, s_model, t_tok, t_model)
            
            cont = input("\nPress Enter to talk again, or 'q' to quit: ")
            if cont.lower() == 'q':
                break
                
    except Exception as e:
        print(f"❌ Error: {e}")