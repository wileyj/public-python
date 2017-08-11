from os import walk
import os
import subprocess
from handbrake import HandBrake


# move list to a dict, with a boolean for each item. ex: 'avi': True
# check as if formats[file extension]: blah
formats = [
    "mkv",
    "avi",
    "AVI"
]

mypath = "/Users/wileyj/Git/wileyj/public-python/convert/testing/files"
handbrake_exe = HandBrake().find_handbrake_executable_in_path("HandBrakeCLI")

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
        newfile = os.path.splitext(item)[0]
        print "Supported file: %s :: %s" % (item, newfile)
        count = count + 1

print "matched: %i" % (count)
print "total: %i" % (len(found))
print "handbrake_exe: %s" % (handbrake_exe)
HandBrake().parse_scan_output(HandBrake().scan_file(handbrake_exe, mypath + "/001-sample.avi"))
# audio_tracks, subtitle_tracks = HandBrake().scan_file(handbrake_exe, mypath + "/001-sample.avi")
# print "Audio Tracks: %s" % (audio_tracks)
# print "subtitle_tracks: %s" % (subtitle_tracks)
