# Aurora Audio Player

This repository contains an audio listener for the Aurora software suite.
The Python script connects to the [core](https://github.com/gewis/narrowcasting-core) using key authentication, connects
to the SocketIO `/audio` namespace and waits for incoming commands. In this
case, this little script plays audio from URLs.

## Prerequisites
- Python 3.11
- VLC (as audio is played using [libvlc](https://wiki.videolan.org/Python_bindings/)).
On Windows, a simple VLC installation should be sufficient.

## Installation
- Create a virtual environment `python -m venv venv`.
- Activate the virtual environment `./venv/Scripts/activate.bat` or `./venv/Scripts/activate`.
- Install requirements `pip install -r requirements.txt`.
- Copy `.env.example` to `.env` and set the URL and authentication key.
- Start the script `python main.py`.

It should now correctly connect to the websocket and listen for incoming commands.
