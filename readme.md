## What am I building?
I am building a Tool that listens to natuaral language voices of the user, recognizes and communicate accordingly.

### what am I using for this?
* this is totally build on python and its frameworks:
* for listenning the voice: 
    1. sounddevice (python framework)
    2. numpy ( a python framework used here for taking digital audio data while recording)
    3. scipy (another python packege used here to build the wav audio file)
* for recognizing: 
    1. whisper (a framework from open-ai very efficient for recognizing natural voices and languages.)
* for speech synthesyzing: 
    1. pyttsx3 ( a pythoon based framework used to produce voice from text.)


## where am I at this bulding process?
* currently I just finished implementing the whole communicating system including whisper and sounddevice to a voice command executer.
* Updated our pipeline, skipped the wav file reading and writing part to enhance speed and efficiency in communication.
* added multi-lingual voice engine program, waiting to be tested and verified.
* dt: $13th Apr 2026$: working on wake word system activation just like real time virtual assistants.

