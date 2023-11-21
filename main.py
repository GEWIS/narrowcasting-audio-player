import os
import socketio
from dotenv import load_dotenv
import vlc
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
player: vlc.MediaPlayer | None = None


def main():
    global sio, player, running

    url = os.environ['URL'] + '/api/auth/mock'
    result = requests.post(url)
    cookie = result.cookies.get('connect.sid')

    # Initialize SocketIO
    sio.connect(os.environ['URL'], headers={'cookie_development': 'connect.sid=' + cookie},
                namespaces=[namespace])

    logging.info('Connected')

    try:
        while running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        running = False
        if player is not None and player.is_playing():
            player.stop()


@sio.event(namespace=namespace)
def play_audio(seconds=0):
    global player
    logging.info('receive play event')

    if player is None:
        return

    if player.play() < 0:
        raise Exception('Could not start playback')

    player.set_time(seconds * 1000)

    sio.emit('play_audio_started', int(time.time() * 1000), namespace=namespace)


@sio.event(namespace=namespace)
def stop_audio():
    global player

    logging.info('receive stop event')
    if player is not None:
        player.stop()


@sio.event(namespace=namespace)
def skip_to(seconds):
    global player

    logging.info('receive skip event: ' + str(seconds))

    if player is None:
        return

    position = seconds * 1000
    player.set_time(position)


@sio.event(namespace=namespace)
def load_audio(url: str):
    global player
    full_url = os.environ['URL'] + url
    logging.info('load audio: ' + full_url)
    stop_audio()

    try:
        # creating a vlc instance
        vlc_instance: vlc.Instance = vlc.Instance()

        # creating a media player
        player = vlc_instance.media_player_new()

        # creating a media
        media: vlc.Media = vlc_instance.media_new(full_url)

        # setting media to the player
        player.set_media(media)

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

