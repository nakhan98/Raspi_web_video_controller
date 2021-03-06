"""
Helper functions
"""

import os
import logging
import json
import subprocess
import pdb
from time import sleep
from shlex import split as sh_split
from threading import Lock
from settings import (STORE_FILE, PLAY_CMD, DIRECTORIES, RESTRICTED_DIRS,
                      FILE_TYPES, WAIT_DURATION)

logging.basicConfig(format='%(asctime)s %(funcName)s: %(message)s',
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')


VIDEOS = []

# Global variable which contains process of video being played
# Should this be a list?
JOBS = []

# Mutex
PLAY_VID_MUTEX = Lock()
SEARCH_VIDS_MUTEX = Lock()

# Omxplayer commands
OMX_MAPPINGS = (
    ("#decrease_speed", 49, "1"),
    ("#increase_speed", 50, "2"),
    ("#rewind", 188, "<"),
    ("#fast_forward", 190, ">"),
    ("#show_info", 90, "z"),
    ("#previous_audio_stream", 74, "j"),
    ("#next_audio_stream", 75, "k"),
    ("#previous_chapter", 73, "i"),
    ("#next_chapter", 79, "o"),
    ("#previous_subtitle_stream", 78, "n"),
    ("#next_subtitle_stream", 77, "m"),
    ("#toggle_subtitles", 83, "s"),
    ("#show_subtitles", 87, "w"),
    ("#hide_subtitles", 88, "x"),
    ("#decrease_subtitle_delay", 68, "d"),
    ("#increase_subtitle_delay", 70, "f"),
    ("#exit_omxplayer", 81, "q"),
    ("#pause_resume_1", 80, "p"),
    ("#pause_resume_2", 32, " "),
    ("#decrease_volume", 189, "-"),
    ("#increase_volume_1", 107, "+"),
    ("#increase_volume_2", 187, "="),
    ("#left_arrow", 37, "\x1b[D"),
    ("#right_arrow", 39, "\x1b[C"),
    ("#up_arrow", 38, "\x1b[A"),
    ("#down_arrow", 40, "\x1b[B")
)


def play_video(video_path):
    """Play video using subprocess.Popen and save process in JOBS"""
    logging.debug("playing video_file: %s", video_path)
    cmd = sh_split(PLAY_CMD.format(video=video_path))
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    if not JOBS:
        JOBS.append({"proc": proc, "video_path": video_path})
        logging.debug("Started omxplayer (pid=%d)", proc.pid)
        while proc.poll() is None:
            logging.debug("video is playing: %s", video_path)
            sleep(10)
        logging.debug("ended playing video: %s", video_path)
        logging.debug("removing process from JOBS")
        del JOBS[-1]
    else:
        logging.warning("omxplayer already running...")


def index_videos():
    """Get list of files in DIRECTORIES (exclude paths in RESTRICTED_DIRS)"""
    logging.debug("preparing to search DIRECTORIES:\n%s",
                  DIRECTORIES)
    file_paths = []
    for dir_ in DIRECTORIES:
        logging.debug("indexing %s...", dir_)
        for root, directories, filenames in os.walk(dir_):
            for filename in filenames:
                if (is_video_file(filename) and not
                        video_restricted(os.path.join(root, filename))):
                    logging.debug("found video file: %s",
                                  filename)
                    file_paths.append(os.path.join(root, filename))
    return file_paths


def video_restricted(video_path):
    """Check video is not from restricted paths"""
    for restricted_dir in RESTRICTED_DIRS:
        if restricted_dir in video_path:
            logging.debug("%s is in restricted dir (%s)",
                          video_path, restricted_dir)
            return True

    return False


def is_video_file(filename):
    """Check if specified file is a video file by checking its file ending"""
    for file_type in FILE_TYPES:
        if filename.endswith(".%s" % file_type):
            return True
    return False


def load_video_list_from_json():
    """
    load list of videos from STORE_FILE and assign to VIDEOS
    """
    global VIDEOS
    SEARCH_VIDS_MUTEX.acquire()
    logging.debug("loading videos from STORE_FILE")
    with open(STORE_FILE) as sf:
        VIDEOS = json.load(sf)["videos"]
        logging.debug("loaded %d videos", len(VIDEOS))
    SEARCH_VIDS_MUTEX.release()


def save_list_of_videos():
    """
    Index videos and then assign to VIDEOS
    """
    global VIDEOS
    SEARCH_VIDS_MUTEX.acquire()
    logging.debug("Preparing to index video files")
    file_paths = index_videos()
    logging.debug("Saving files to json store")
    with open(STORE_FILE, "wt") as fh:
        json.dump({"videos": file_paths}, fh)
    VIDEOS = file_paths
    logging.debug("Finished indexing.")
    SEARCH_VIDS_MUTEX.release()


def load_and_reindex_videos():
    """
    Load list of videos from STORE_FILE and then periodically re-index
    DIRECTORIES. Expected to be run in a separate thread.
    """
    try:
        load_video_list_from_json()
    except IOError:
        logging.debug("not found STORE_FILE: %s", STORE_FILE)
        logging.debug("will search for videos now")
        save_list_of_videos()
    finally:
        while True:
            """
            logging.debug("Preparing to spin off thread")
            thread = threading.Thread(target=search_files)
            thread.start()
            thread.join()
            """
            sleep(WAIT_DURATION)
            save_list_of_videos()


def search_vids(search_term):
    """Search for video in VIDEOS"""
    logging.debug("searching for %s", search_term)
    try:
        search_results = [i for i in VIDEOS if search_term.upper() in
                          i.upper()][:100]
        # search_results = find_matches(search_term)
    except Exception as err:
        logging.warning("error occurred: %s", err)
        search_results = []
    finally:
        return search_results
