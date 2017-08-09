from os import walk
import os

formats = [
    "mkv",
    "avi",
    "AVI"
]

mypath = "/Users/wileyj/Git/wileyj/public-python/convert/testing/files"
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
