import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import whisper
import pyttsx3

#setting up the TTS
engine = pyttsx3.init()
voice = engine.getProperty("voices")
engine.setProperty("voice",voice[0].id)
engine.setProperty('rate',150)
engine.setProperty('volume',1.0)

#the listening part
fs = 16000
duration = 10  # max duration
threshold = 0.01  # silence threshold

print("Speak...")

recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
sd.wait()

# Trim silence
audio = recording.flatten()

# Find where sound starts/stops
indices = np.where(np.abs(audio) > threshold)[0]

if len(indices) > 0:
    start = indices[0]
    end = indices[-1]
    trimmed_audio = audio[start:end]
else:
    trimmed_audio = audio

# Convert to int16
trimmed_audio = (trimmed_audio * 32767).astype(np.int16)

write("output.wav", fs, trimmed_audio)



#the recognizing part
model = whisper.load_model("base")

try:
    #the telling part
    result = model.transcribe("output.wav")
    print("You said: ",result["text"])
    text = result["text"]

    #TTS response
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


    