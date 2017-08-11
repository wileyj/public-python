import re


class HandBrakeAudioInfo(object):
    pattern1 = re.compile(r"(\d+), (.+) \(iso639-2: ([a-z]{3})\)")
    pattern2 = re.compile(r"(\d+), (.+) \(iso639-2: ([a-z]{3})\), (\d+)Hz, (\d+)bps")

    def __init__(self, info_str):
        match = self.pattern1.match(info_str)
        print "Info_str: %s" % (info_str)
        print "Match: %s" % (match)
        if not match:
            raise ValueError("Unknown audio track info format: " + repr(info_str))
        print "Line 12"
        self.index = int(match.group(1))
        self.description = match.group(2)
        self.language_code = match.group(3)
        match = self.pattern2.match(info_str)
        print "Line 17"
        if match:
            print "Line 19"
            self.sample_rate = int(match.group(4))
            self.bit_rate = int(match.group(5))
        else:
            print "Line 23"
            self.sample_rate = None
            self.bit_rate = None
        self.title = None

    def __str__(self):
        print "Line 29"
        format_str = (
            "Description: {description}\n"
            "Language code: {language_code}"
        )
        print "Line 34"
        if self.sample_rate:
            print "Line 36"
            format_str += "\nSample rate: {sample_rate}Hz"
        if self.bit_rate:
            print "Line 39"
            format_str += "\nBit rate: {bit_rate}bps"
        return format_str.format(**self.__dict__)

    def __hash__(self):
        print "Line 44"
        return hash((
            self.index,
            self.description,
            self.language_code,
            self.sample_rate,
            self.language_code,
            self.title
        ))

    def __eq__(self, other):
        print "Line 55"
        if not isinstance(other, HandBrakeAudioInfo):
            print "Line 57"
            return False
        print "Line 59"
        return (
            self.index == other.index and
            self.description == other.description and
            self.language_code == other.language_code and
            self.sample_rate == other.sample_rate and
            self.language_code == other.language_code and
            self.title == other.title
        )
