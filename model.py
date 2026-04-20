# Always listening → Detect trigger → Activate → Process → Respond → Go back to listening
"""
The architecture: 
Loop:
    Listen (short audio)
    ↓
    Convert to text
    ↓
    If wake word → full processing
    Else → ignore
"""

import sounddevice as sd
import numpy as np
import queue
import json
import whisper
import win32com.client
import pythoncom
from vosk import Model, KaldiRecognizer

# setup
pythoncom.CoInitialize()
engine = win32com.client.Dispatch("SAPI.SpVoice")

model = whisper.load_model("tiny")
model_path = "model/en-us/vosk-model-small-en-us-0.15"

vosk_model = Model(model_path)
recognizer = KaldiRecognizer(vosk_model, 16000)

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))


def ask_AI(user_input, chat_history_ids=None):
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch

    tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
    model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-small")
        
    # Add EOS token if not present
    if tokenizer.eos_token is None:
        tokenizer.eos_token = tokenizer.pad_token

    chat_history_ids = None

    while True:

        # Encode user input
        new_user_input_ids = tokenizer.encode(user_input + tokenizer.eos_token, return_tensors='pt')

        # Append to chat history
        if chat_history_ids is not None:
            bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids], dim=-1)
        else:
            bot_input_ids = new_user_input_ids

        # Generate response
        chat_history_ids = model.generate(
            bot_input_ids,
            max_length=1000,
            pad_token_id=tokenizer.eos_token_id,
            no_repeat_ngram_size=3,
            do_sample=True,
            top_k=100,
            top_p=0.7,
            temperature=0.8
        )

        # Decode response
        response = tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
        return f"{response}"

# command system
def process_command(text):
    if "open youtube" in text:
        import webbrowser
        webbrowser.open("https://youtube.com")
        return "Opening YouTube", "open_youtube"

    elif "time" in text:
        import datetime
        now = datetime.datetime.now().strftime("%H:%M")
        return f"The time is {now}", "time"

    elif "hello" in text:
        return "Hello Karan", "greeting"

    elif "exit" in text or "quit" in text:
        return "Goodbye", "exit"
    elif "what is your name?" in text:
        return "I am your servant sir.", "roduction"

    else:
        return f"{ask_AI(text)}","AI response"

# record function
def record_command(duration=4, fs=16000):
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    audio = recording.flatten().astype(np.float32)
    return audio

# main loop
print("🎤 Assistant is running...")

stream = sd.RawInputStream(
    samplerate=16000,
    blocksize=8000,
    dtype='int16',
    channels=1,
    callback=callback
)

with stream:
    while True:
        print("Listening for wake word...")

        data = q.get()

        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").lower()

            print("Heard:", text)

            if "servant" in text:
                print("✅ Activated")

                engine.Speak("Yes?")

                # record command
                audio = record_command()

                # whisper transcription
                result = model.transcribe(audio)
                command = result["text"].lower().strip()

                print("Command:", command)

                # process command
                response, action = process_command(command)

                print("Response:", response)
                engine.Speak(response)

                if action == "exit":
                    break