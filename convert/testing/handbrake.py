import logging
import os
import subprocess


class FFmpegStreamInfo(object):
    def __init__(self, stream_index, codec_type, codec_name, language_code, metadata):
        self.stream_index = stream_index
        self.codec_type = codec_type
        self.codec_name = codec_name
        self.language_code = language_code
        self.metadata = metadata


class HandBrake():

    def parse_scan_output(self, input):
        lines = input.splitlines()
        i = 0
        while i < len(lines):
            print "Line: %s" % (lines[i])
            i += 1
        return True

    def scan_file(self, handbrake_exe, filename):
        logging.critical("Using Handbrake exe: %s" % (handbrake_exe))
        logging.critical("Checking on file: %s" % (filename))
        output = subprocess.check_output([
            handbrake_exe,
            "-i", filename,
            "--scan"
        ], stderr=subprocess.STDOUT)
        return output.decode("utf-8")

    def check_handbrake_executable(self, file_path):
        if not os.path.isfile(file_path):
            return False
        message_format = "Found HandBrakeCLI binary at '%s'"
        if not os.access(file_path, os.X_OK):
            message_format += ", but it is not executable"
            logging.warning(message_format, file_path)
            return False
        logging.info(message_format, file_path)
        return True

    def find_handbrake_executable_in_path(self, name):
        path_env = os.environ.get("PATH", os.defpath)
        path_env_split = path_env.split(os.pathsep)
        path_env_split.insert(0, os.path.abspath(os.path.dirname(__file__)))
        for dir_path in path_env_split:
            file_path = os.path.join(dir_path, name)
            if HandBrake().check_handbrake_executable(file_path):
                return file_path
        return None