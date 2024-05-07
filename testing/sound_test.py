from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio, play
from time import sleep

# import file as wav
sound = AudioSegment.from_file("./tracks/madeofsmoke/bass.mp3", format="mp3")
# this makes the volume manageable?
sound = sound.set_sample_width(2)
# first 10 seconds, slicing is done in ms
start = sound[5000:15000]
# reduce volume by 2
start_quiet = start - 2
# play song
#play(start_quiet)
playback = _play_with_simpleaudio(start_quiet)
sleep(5)
print(playback.is_playing())
playback.stop()
sleep(3)
print(playback.is_playing())



