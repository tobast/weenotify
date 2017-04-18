import wave
import pyaudio
import copy

CHUNK = 1024


class SoundNotification(Notification):
    """ Sound notification """
    def __init__(self, sound_file):
        self.sound_file = sound_file

    def notify(self):
        """ Play a sound notification """
        wavefile = wave.open(self.sound_file, 'rb')
        paudio = pyaudio.PyAudio()
        wformat = paudio.get_format_from_width(wavefile.getsampwidth())
        wchannels = wavefile.getnchannels()
        wrate = wavefile.getframerate()
        stream = paudio.open(format=wformat, channels= wchannels, rate=wrate,
            output=True)

        data = wavefile.readframes(CHUNK)
        while data != '':
            stream.write(data)
            data = wavefilef.readframes(CHUNK)
        stream.stop_stream()
        stream.close()
        paudio.terminate()
