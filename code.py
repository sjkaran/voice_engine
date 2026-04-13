import speech_recognition as sr
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import pyttsx3


# voice listening and replying without using whisper
# requires internet connection and less accurate.

# TTS setup
engine = pyttsx3.init()

# Record audio
fs = 44100
seconds = 4

print("Speak...")
recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
sd.wait()

recording = (recording * 32767).astype(np.int16)
write("output.wav", fs, recording)

# STT
recognizer = sr.Recognizer()

with sr.AudioFile("output.wav") as source:
    audio = recognizer.record(source)

try:
    text = recognizer.recognize_google(audio)
    print("You said:", text)

    # TTS response
    engine.say(f"You said {text}")
    engine.runAndWait()

except Exception as e:
    print("Error:", e)
    engine.say("I did not understand you.")
    engine.runAndWait()