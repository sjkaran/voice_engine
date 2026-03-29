import speech_recognition as sr
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import pyttsx3

engine = pyttsx3.init()
voice = engine.getProperty('voices')

engine.setProperty('voice',voice[0].id)
engine.setProperty('rate',150)
engine.setProperty('volume',1.0)

fs = 44100
seconds = 4

print("Speak now:")
recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
sd.wait()

recording = (recording * 32767).astype(np.int16)
write("output.wav",fs,recording)

recognizer = sr.Recognizer()

with sr.AudioFile("output.wav") as source:
    audio = recognizer.record(source)

try:
    text = recognizer.recognize_google(audio)
    print("you said: ", text)

    # TTS response
    if "fuck" in text:
        print("Fuck you man stop cursing.")
        engine.say("Fuck you man stop cursing")
        engine.runAndWait()
    elif "you are great" in text:
        print("I know that, You are great too.")
        engine.say(f"I know that, You are great too.")
        engine.runAndWait()
    else:
        engine.say(f"{text}. thats all I heared.")
        engine.runAndWait()

except Exception as e:
    print("Error", e)
    engine.say("I did not get you bro.")
    engine.runAndWait()