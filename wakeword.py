import sounddevice as sd
import queue
import json
from vosk import Model, KaldiRecognizer
import win32com.client
import pythoncom

q = queue.Queue()
pythoncom.CoUninitialize()
vengine = win32com.client.Dispatch("SAPI.SpVoice")

def callback(indata, frames, time, status):
    q.put(bytes(indata))

model_path = "model/vosk-model-small-en-in-0.4"
model = Model(model_path)
recognizer = KaldiRecognizer(model, 16000)

stream = sd.RawInputStream(
    samplerate=16000,
    blocksize=8000,
    dtype='int16',
    channels=1,
    callback=callback
)

print("Listening for wake word...")

with stream:
    while True:
        data = q.get()
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text","")
            print("Heard:",text)

            if "servant" in text:
                print("Activated!")
                vengine.Speak("I am your Servant sir...")
                break

