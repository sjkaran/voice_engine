import whisper
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

fs = 16000
duration = 10 # max duration
threshold = 0.01 # silence threshold

print("Speak...")

recording = sd.rec(int(duration * fs),samplerate = fs, channels=1)
sd.wait()

# Trim silence
audio = recording.flatten()

#find where sound starts/stops
indices = np.where(np.abs(audio) > threshold)[0]

if len(indices) > 0:
    start = indices[0]
    end = indices[-1]
    trimmed_audio = audio[start:end]
else:
    trimmed_audio = audio

# Convert to int16
trimmed_audio = (trimmed_audio * 32767).astype(np.int16)

write("output.wav",fs,trimmed_audio)

model = whisper.load_model("base")  # try tiny/base/small
result = model.transcribe("output.wav")
print("You said:", result["text"])