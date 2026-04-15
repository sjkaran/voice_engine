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

model = whisper.load_model("base")
model_path = "model/en-us/vosk-model-small-en-us-0.15"

vosk_model = Model(model_path)
recognizer = KaldiRecognizer(vosk_model, 16000)

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

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
        return "I am Abhijit", "introduction"

    else:
        return "I did not understand that", "unknown"

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

            if "hello" in text:
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