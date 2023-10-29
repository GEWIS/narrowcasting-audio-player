import socketio
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
from simpleaudio.shiny import PlayObject
import time
import requests
import logging
import traceback


running = True
sio = socketio.Client()
audio_original: AudioSegment
audio_timestamped: AudioSegment | None = None
playback: PlayObject | None = None


def main():
    global sio, audio_original, playback, running

    url = 'http://localhost:3000/auth/mock'
    result = requests.post(url)
    cookie = result.cookies.get('connect.sid')

    print(cookie)

    # Initialize SocketIO
    sio.connect('http://127.0.0.1:3000', headers={'cookie_development': 'connect.sid=' + cookie},
                namespaces=['/audio'])

    # Load audio file from a remote source (replace 'your_audio_url' with the actual URL)
    audio_url = 'rick.mp3'
    audio_original = AudioSegment.from_mp3(audio_url)

    print('Connected')

    try:
        while running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        running = False
        if playback is not None and playback.is_playing():
            playback.stop()


@sio.event(namespace='/audio')
def play_audio():
    global playback, audio_original, audio_timestamped
    print('receive play event')

    if audio_timestamped is not None:
        playback = _play_with_simpleaudio(audio_timestamped)
        audio_timestamped = None
    else:
        playback = _play_with_simpleaudio(audio_original)


@sio.event(namespace='/audio')
def stop_audio():
    global playback

    print('receive stop event')
    playback.stop()


@sio.event(namespace='/audio')
def skip_to(seconds):
    global audio_original, playback, audio_timestamped

    audio_timestamped = audio_original[seconds * 1000:]
    if playback.is_playing():
        playback.stop()
        playback = _play_with_simpleaudio(audio_timestamped)
        audio_timestamped = None


if __name__ == '__main__':
    while running:
        try:
            main()
        except Exception as e:
            logging.error(traceback.format_exc())
            print('Something went wrong. Try again after 5 seconds...')
            time.sleep(5)

