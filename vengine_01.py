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

import whisper
import sounddevice as sd
import numpy as np
import win32com.client
import pythoncom
from scipy.io.wavfile import write

pythoncom.CoUninitialize()
engine = win32com.client.Dispatch("SAPI.SpVoice")

fs = 16000
duration = 2
threshold = 0.01
model = whisper.load_model("base")

def process_command(text): #step 2
    if "open youtube" in text:
        return "Opening Youtube", "open_youtube"
    elif "what is your name?" in text:
        return "I am your servent sir.","identity"
    elif any(word in text for word in ["time","clock","current time"]):
        import datetime
        now = datetime.datetime.now().strftime("%H:%M")
        return f"The time is {now}","time"
    elif any(word in text for word in ["hello", "hi","hey","whatsup"]):
        return "Hello Karan","greeting"
    elif any(word in text for word in ["close","quit","exit"]):
        return "Closing", "exit"
    else:
        return "I did not get you sir.", "unknown"

buffer = np.array([], dtype=np.float32)

while True:
    recording = sd.rec(int(2 * fs), samplerate=fs, channels=1)
    sd.wait()

    chunk = recording.flatten().astype(np.float32)

    # 🔥 accumulate audio
    buffer = np.concatenate((buffer, chunk))

    # keep only last ~4 seconds
    if len(buffer) > fs * 4:
        buffer = buffer[-fs*4:]

    result = model.transcribe(buffer)
    text = result["text"].lower().strip()

    print("Heard:", text)

    if "assistant" in text:
        print("Activated!")
        break
    
    if "servant" in text:
        print("Activated!")

        engine.Speak("Yes?")

        # now record full command
        recording = sd.rec(int(4 * fs), samplerate=fs, channels=1)
        sd.wait()

        audio = recording.flatten()
        audio = audio.astype(np.float32)

        result = model.transcribe(audio)
        command = result["text"].lower().strip()

        print("Command:", command)

        response, action = process_command(command)

        engine.Speak(response)