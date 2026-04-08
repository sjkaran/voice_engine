import torch
from transformers import pipeline

audio = "output.wav"
device = "cuda:0" if torch.cuda.is_available() else "cpu"
modelTags = "ARTPARK-IISc/whisper-large-v3-vaani-odia"

transcribe = pipeline(
    task="automatic-speech-recognition",
    model=modelTags,
    chunk_length_s=30,
    device=device
)


transcribe.model.config.forced_decoder_ids = None
transcribe.model.generation_config.forced_decoder_ids = None

print("Transcription:", transcribe(audio)["text"])
