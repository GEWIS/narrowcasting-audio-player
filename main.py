import os
from io import BytesIO
import socketio
from dotenv import load_dotenv
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
from simpleaudio.shiny import PlayObject
import time
import requests
import logging
import traceback

load_dotenv()
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)

namespace = '/audio'
running = True
sio = socketio.Client(logger=True)
audio_original: AudioSegment | None = None
audio_timestamped: AudioSegment | None = None
playback: PlayObject | None = None


def main():
    global sio, audio_original, playback, running

    url = os.environ['URL'] + '/api/auth/mock'
    result = requests.post(url)
    cookie = result.cookies.get('connect.sid')

    # Initialize SocketIO
    sio.connect(os.environ['URL'], headers={'cookie_development': 'connect.sid=' + cookie},
                namespaces=[namespace])

    print('Connected')

    try:
        while running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        running = False
        if playback is not None and playback.is_playing():
            playback.stop()


@sio.event(namespace=namespace)
def play_audio():
    global playback, audio_original, audio_timestamped
    print('receive play event')

    if audio_timestamped is not None:
        playback = _play_with_simpleaudio(audio_timestamped)
        audio_timestamped = None
    else:
        playback = _play_with_simpleaudio(audio_original)

    sio.emit('play_audio_started', int(time.time() * 1000), namespace=namespace)


@sio.event(namespace=namespace)
def stop_audio():
    global playback

    print('receive stop event')
    if playback is not None:
        playback.stop()


@sio.event(namespace=namespace)
def skip_to(seconds):
    global audio_original, playback, audio_timestamped

    audio_timestamped = audio_original[seconds * 1000:]
    if playback and playback.is_playing():
        playback.stop()
        playback = _play_with_simpleaudio(audio_timestamped)
        audio_timestamped = None


@sio.event(namespace=namespace)
def load_audio(url: str):
    global playback, audio_original
    logging.info('load audio: ' + url)
    stop_audio()

    try:
        # Fetch file from source
        res = requests.get(os.environ['URL'] + url)
        if res.status_code >= 300:
            raise Exception('Status code ' + str(res.status_code), res.content)

        file_name, file_extension = os.path.splitext(url)
        logging.info('Fetched audio file. Now initializing...')
        audio_original = AudioSegment.from_file(BytesIO(res.content), file_extension[1:])

        sio.emit('load_audio_success', namespace=namespace)
        logging.info('Audio file initialized!')
    except Exception as e:
        logging.error(traceback.format_exc())
        sio.emit('load_audio_fail', namespace=namespace)


if __name__ == '__main__':
    while running:
        try:
            main()
        except Exception as e:
            logging.error(traceback.format_exc())
            print('Something went wrong. Try again after 5 seconds...')
            time.sleep(5)

