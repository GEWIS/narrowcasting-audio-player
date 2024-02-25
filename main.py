import os
import socketio
from dotenv import load_dotenv
import vlc
import time
import requests
import logging
import traceback
import math
from threading import Thread
from urllib.parse import urljoin

load_dotenv()
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)

namespace = '/audio'
running = True
sio = socketio.Client(logger=True)
player: vlc.MediaPlayer | None = None

sync_thread: Thread | None = None
sync_thread_running = False
last_audio_sync = 0


def sync_audio_timings():
    global sync_thread_running, last_audio_sync

    while sync_thread_running:
        now = time.time()
        # Synchronize every 30 seconds if audio is playing
        if now - last_audio_sync >= 30 and player is not None and player.is_playing() and player.get_time() >= 0:
            last_audio_sync = now
            player_ms = player.get_time()
            now_ms = math.floor(time.time_ns() / 1000000)
            sio.emit('sync_audio_timings', {
                'startTime': now_ms,
                'timestamp': player_ms,
            }, namespace=namespace)

        time.sleep(0.1)


def create_sync_loop():
    global sync_thread, sync_thread_running

    sync_thread_running = True
    sync_thread = Thread(target=sync_audio_timings)
    sync_thread.daemon = True
    sync_thread.start()


def stop_sync_loop():
    global sync_thread, sync_thread_running

    if sync_thread is None:
        return

    sync_thread_running = False
    sync_thread.join()


def main():
    global sio, player, running

    url = os.environ['URL'] + '/api/auth/key'
    result = requests.post(url, {'key': os.environ['API_KEY']})

    if result.status_code != 200:
        json = result.json()
        raise Exception("Could not authenticate with core: [HTTP {}]: {}".format(
            result.status_code,
            json['details'] if json['details'] else json['message']),
        )

    cookie = result.cookies.get('connect.sid')

    def get_headers():
        return {'cookie': 'connect.sid=' + cookie}

    # Initialize SocketIO
    sio.connect(os.environ['URL'], headers=get_headers,
                namespaces=['/', namespace])

    logging.info('Connected')

    try:
        while running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        running = False
        stop_audio()


@sio.event(namespace=namespace)
def play_audio(url: str, seconds=0):
    global player
    logging.info('receive play event')

    load_audio(url)

    if player is None:
        return

    if player.play() < 0:
        raise Exception('Could not start playback')

    if seconds is not None:
        skip_to(seconds)

    sio.emit('play_audio_started', int(time.time() * 1000), namespace=namespace)

    # Start a synchronization worker
    create_sync_loop()


@sio.event(namespace=namespace)
def stop_audio():
    global player

    logging.info('receive stop event')

    # Stop the synchronization thread
    stop_sync_loop()

    if player is not None:
        player.pause()


@sio.event(namespace=namespace)
def skip_to(seconds):
    global player

    logging.info('receive skip event: ' + str(seconds))

    if player is None:
        return

    position = int(seconds * 1000)
    player.set_time(position)


def load_audio(url: str):
    global player

    if url.startswith('http'):
        full_url = url
    else:
        full_url = urljoin(os.environ['URL'], url)

    logging.info('load audio: ' + full_url)

    if player:
        player.stop()

    try:
        # creating a vlc instance
        vlc_instance: vlc.Instance = vlc.Instance()

        # creating a media player
        player = vlc_instance.media_player_new()

        # creating a media
        media: vlc.Media = vlc_instance.media_new(full_url)

        # setting media to the player
        player.set_media(media)

        logging.info('Audio file initialized!')
    except Exception as e:
        logging.error(traceback.format_exc())


@sio.event
def disconnect():
    global player

    if player:
        player.stop()
        player = None


if __name__ == '__main__':
    while running:
        try:
            main()
        except Exception as e:
            logging.error(traceback.format_exc())
            print('Something went wrong. Try again after 5 seconds...')
            time.sleep(5)

