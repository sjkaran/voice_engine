# need to achieve parallel threading in order to enhance the voice engine,

"""
Thread 1: detects the speech activity and keeps alive the thread 2.
Thread 2: continue recording till thread 1 shows a signal to stop.
Thread 2 stops and sends the data for recognition.

"""