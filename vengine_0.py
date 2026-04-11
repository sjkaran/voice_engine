import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import whisper
import win32com.client
import pythoncom 



#the listening part
def listening_recognize():
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

    audio = np.array(trimmed_audio)

    audio = audio.astype(np.float32) /32768.0

    model = whisper.load_model("base")
    
    try:
        result = model.transcribe(audio)
        print("You said: ",result["text"])
        text = result["text"].lower().strip() # step 1: normalization of input
        return text
    except Exception as e:
        print("Error",e)
        return "I can't understand your command."

    

def process_commands(text): #step 2
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


while True: #step 3 execute actions
    text = listening_recognize()
    response, action = process_commands(text)
    print(response)
    try:
         # 1. Initialize a clean memory state for THIS specific thread
        pythoncom.CoInitialize()
        # 2. Directly hook into Windows native text-to-speech (Bypassing pyttsx3)
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Speak(response)
    except Exception as e:
        print(f"Audio Error: {e}")
    finally:
         # 3. CRITICAL: Destroy the object immediately after speaking.
         # It leaves zero footprint, guaranteeing the next click will work flawlessly.         
        pythoncom.CoUninitialize()

    #codes for action handling
    if action == "exit":
        break

