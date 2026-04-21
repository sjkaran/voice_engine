import torch
import scipy.io.wavfile
from transformers import VitsModel, AutoTokenizer

with open("API_KEY.txt","r")as key:
    HF_TOKEN = key.readline()

# 2. Configuration
MODEL_ID = "facebook/mms-tts-ory"  # 'ory' is the ISO code for Odia
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def odia_text_to_speech(text, output_filename="odia_output.wav"):
    print(f"Loading TTS Engine on {DEVICE}...")
    
    # Load Tokenizer and Model
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
    model = VitsModel.from_pretrained(MODEL_ID, token=HF_TOKEN).to(DEVICE)

    # Clean and Tokenize input
    inputs = tokenizer(text, return_tensors="pt").to(DEVICE)

    # Generate Audio
    print("Generating voice...")
    with torch.no_grad():
        output = model(**inputs).waveform

    # Save to file
    audio_data = output[0].cpu().numpy()
    scipy.io.wavfile.write(output_filename, rate=model.config.sampling_rate, data=audio_data)
    
    print(f"✅ Success! File saved as: {output_filename}")

# --- RUN IT ---
if __name__ == "__main__":
    # Put your Odia text here
    my_text = "ନମସ୍କାର, ଆପଣ କେମିତି ଅଛନ୍ତି?" 
    
    odia_text_to_speech(my_text)