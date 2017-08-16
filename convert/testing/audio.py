import re
import logging

log_format = '[%(levelname)-s] %(filename)-s %(funcName)-4s(%(lineno)-s) - %(message)-4s'
logging.basicConfig(level=logging.INFO, format=log_format)


class HandBrakeAudioInfo(object):
    pattern1 = re.compile(r"(\d+), (.+) \(iso639-2: ([a-z]{3})\)")
    pattern2 = re.compile(r"(\d+), (.+) \(iso639-2: ([a-z]{3})\), (\d+)Hz, (\d+)bps")

    def __init__(self, info_str):
        match = self.pattern1.match(info_str)
        logging.info("Info_str: %s" % (info_str))
        logging.info("Match pattern1: %s" % (match))
        if not match:
            raise ValueError("Unknown audio track info format: " + repr(info_str))
        logging.info("")
        self.index = int(match.group(1))
        self.description = match.group(2)
        self.language_code = match.group(3)
        logging.info("match1 index:: %s" % (self.index))
        logging.info("match1 description:: %s" % (self.description))
        logging.info("match1 language_code:: %s" % (self.language_code))
        match = self.pattern2.match(info_str)
        logging.info("Match pattern2: %s" % (match))
        logging.info("")
        if match:
            logging.info("match:: %s" % (match))
            self.sample_rate = int(match.group(4))
            self.bit_rate = int(match.group(5))
        else:
            logging.info("not match:: %s" % (match))
            self.sample_rate = None
            self.bit_rate = None
        self.title = None

    def __str__(self):
        logging.info("line:: ")
        format_str = (
            "Description: {description}\n"
            "Language code: {language_code}"
        )
        logging.info("line:: ")
        if self.sample_rate:
            logging.info("sample_rate:: ")
            format_str += "\nSample rate: {sample_rate}Hz"
        if self.bit_rate:
            logging.info("bit_rate:: ")
            format_str += "\nBit rate: {bit_rate}bps"
        return format_str.format(**self.__dict__)

    def __hash__(self):
        logging.info("hash:: ")
        return hash((
            self.index,
            self.description,
            self.language_code,
            self.sample_rate,
            self.language_code,
            self.title
        ))

    def __eq__(self, other):
        logging.info("")
        if not isinstance(other, HandBrakeAudioInfo):
            logging.info("")
            return False
        logging.info("")
        return (
            self.index == other.index and
            self.description == other.description and
            self.language_code == other.language_code and
            self.sample_rate == other.sample_rate and
            self.language_code == other.language_code and
            self.title == other.title
        )
