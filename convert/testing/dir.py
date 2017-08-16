from os import walk
import os
import subprocess
from handbrake import HandBrake
import logging

# move list to a dict, with a boolean for each item. ex: 'avi': True
# check as if formats[file extension]: blah
formats = [
    "mkv",
    "avi",
    "AVI",
    "mp4",
    "MOV",
    "m4v",
    "mov"
]

# mypath = "/Users/wileyj/Git/wileyj/public-python/convert/testing/files"
# mypath = "/Volumes/Media/Music/iTunes/iTunes Media/Home Videos/"
mypath = "/Volumes/wileyj/Desktop/To Convert"
handbrake_exe = HandBrake().find_handbrake_executable_in_path("HandBrakeCLI")
log_format = '[%(levelname)-s] %(filename)-s %(funcName)-4s(%(lineno)-s) - %(message)-4s'
logging.basicConfig(level=logging.INFO, format=log_format)

found = []
for (dirpath, dirnames, filenames) in walk(mypath):
    found.extend(filenames)
    break

# for k, v in enumerate(found):
#     found[k] = mypath + "/" + found[k]


class MatchFile():
    def format(self, filename):
        for format in formats:
            if filename.endswith(format):
                return True


count = 0
for item in found:
    if MatchFile().format(item):
        count = count + 1
        newfile = os.path.splitext(item)[0]
        logging.info("%i) Supported file: %s :: %s" % (count, item, newfile))
        HandBrake().parse_scan_output(HandBrake().scan_file(handbrake_exe, mypath + "/" + item))
        audio_tracks = HandBrake().scan_file(handbrake_exe, mypath + "/" + item)
        logging.info("Audio Tracks: %s" % (audio_tracks))
        # logging.info("subtitle_tracks: %s" % (subtitle_tracks))

logging.info("matched: %i" % (count))
logging.info("handbrake_exe: %s" % (handbrake_exe))
# HandBrake().parse_scan_output(HandBrake().scan_file(handbrake_exe, mypath + "/001-sample.avi"))
# HandBrake().parse_scan_output(HandBrake().scan_file(handbrake_exe, "/Volumes/Media/Music/iTunes/iTunes Media/Home Videos/Total Body - Yoga Fix.m4v"))
# audio_tracks, subtitle_tracks = HandBrake().scan_file(handbrake_exe, mypath + "/001-sample.avi")
# logging.info("Audio Tracks: %s" % (audio_tracks))
# logging.info("subtitle_tracks: %s" % (subtitle_tracks))
