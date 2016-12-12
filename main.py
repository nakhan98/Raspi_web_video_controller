#!/usr/bin/env python2
"""
Raspi_web_video_controller
---------
Flask web app to to search for video files in specified folders and play them
on my raspberry pi using omxplayer.

Basic web controls to control video playback.

Quite rough at the moment, needs a lot more work. More details to follow.

Issues
------
- https://www.raspberrypi.org/forums/viewtopic.php?t=114786
- http://stackoverflow.com/questions/30743490
"""

import threading
import pdb
import os.path
from time import sleep
from flask import Flask, url_for, render_template, jsonify, request
from helpers import (load_and_reindex_videos, search_vids, logging, JOBS,
                     play_video, OMX_MAPPINGS)

APP = Flask(__name__)


@APP.route('/')
def index():
    return render_template("search_page.html")


@APP.route("/ajax/search/<search>")
def search_file(search):
    results = search_vids(search)
    return jsonify(
        {"number_of_results": len(results),
         "results": results
         }
    )


@APP.route("/play/<encoded_video_path>")
def vid_details(encoded_video_path):
    logging.debug("asked details for: %s", encoded_video_path)
    video_path = encoded_video_path.decode("base64", "strict")
    logging.debug("decoded path: %s", video_path)
    new_thread = threading.Thread(target=play_video, args=(video_path,))
    new_thread.start()
    logging.debug("spun off thread to play video")
    while not JOBS:
        logging.debug("waiting for omxplayer process...")
        sleep(1)
    pid = JOBS[-1]["proc"].pid
    video_file = os.path.basename(JOBS[-1]["video_path"])
    return render_template("video_play.html", video_path=video_path,
                           video_file=video_file, pid=pid)


@APP.route("/ajax/omx_char", methods=['POST'])
def comm_omx():
    key_press = request.json["keypress"]
    logging.debug("recieved: %s", key_press)
    char = [i[2] for i in OMX_MAPPINGS if i[1] == key_press]
    error = None
    if char:
        try:
            logging.debug("sending char to process: %s", char[0])
            JOBS[-1]["proc"].stdin.write(char[0])
        except IndexError:
            error = "Omxplayer process is not running"
    return jsonify({"error": error})


@APP.route("/ajax/omxplayer_cmd", methods=['POST'])
def control_omx():
    command = request.json["command"]
    logging.debug("received: %s", command)
    omx_command = [i[2] for i in OMX_MAPPINGS if i[0] == command]
    error = None
    if omx_command:
        try:
            logging.debug("sending char to process: %s", omx_command[0])
            JOBS[-1]["proc"].stdin.write(omx_command[0])
        except IndexError:
            error = "Omxplayer process is not running"
    return jsonify({"error": error})


if __name__ == '__main__':
    t1 = threading.Thread(target=load_and_reindex_videos)
    t1.start()
    APP.run(host='0.0.0.0', port=8080, debug=True)
