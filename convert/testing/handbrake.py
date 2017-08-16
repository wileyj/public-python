import logging
import os
import subprocess
from audio import HandBrakeAudioInfo

log_format = '[%(levelname)-s] %(filename)-s %(funcName)-4s(%(lineno)-s) - %(message)-4s'
logging.basicConfig(level=logging.INFO, format=log_format)


class FFmpegStreamInfo(object):
    def __init__(self, stream_index, codec_type, codec_name, language_code, metadata):
        self.stream_index = stream_index
        self.codec_type = codec_type
        self.codec_name = codec_name
        self.language_code = language_code
        self.metadata = metadata


class HandBrake():
    def parse_handbrake_scan_output(output):
        lines = output.splitlines()
        hb_audio_tracks = None
        hb_subtitle_tracks = None
        ff_audio_streams = None
        ff_subtitle_streams = None
        i = 0
        while i < len(lines):
            if lines[i].startswith("Input #0, "):
                logging.debug("Found FFmpeg stream info")
                i, ff_audio_streams, ff_subtitle_streams = HandBrake().parse_ffmpeg_stream_info(lines, i)
                message_format = "FFmpeg: %d audio track(s), %d subtitle track(s)"
                logging.debug(message_format, len(ff_audio_streams), len(ff_subtitle_streams))
                continue
            if lines[i] == "  + audio tracks:":
                logging.debug("Found HandBrake audio track info")
                i, hb_audio_tracks = HandBrake().parse_handbrake_track_info(lines, i, HandBrakeAudioInfo)
                logging.debug("HandBrake: %d audio track(s)", len(hb_audio_tracks))
                continue
            if lines[i] == "  + subtitle tracks:":
                logging.debug("Found HandBrake subtitle track info")
                i, hb_subtitle_tracks = HandBrake().parse_handbrake_track_info(lines, i, HandBrake().HandBrakeSubtitleInfo)
                logging.debug("HandBrake: %d subtitle track(s)", len(hb_subtitle_tracks))
                continue
            i += 1
        HandBrake().merge_track_titles(hb_audio_tracks, ff_audio_streams)
        HandBrake().merge_track_titles(hb_subtitle_tracks, ff_subtitle_streams)
        return (hb_audio_tracks, hb_subtitle_tracks)

    def merge_track_titles(hb_tracks, ff_streams):
        if not ff_streams:
            return
        assert len(hb_tracks) == len(ff_streams), "Track count mismatch"
        for hb_track, ff_stream in zip(hb_tracks, ff_streams):
            assert hb_track.language_code == ff_stream.language_code, "Track language code mismatch"
            hb_track.title = ff_stream.metadata.get("title")

    def parse_handbrake_track_info(self, output_lines, start_index, info_cls):
        prefix = "    + "
        prefix_len = len(prefix)
        tracks = []
        i = start_index + 1
        while i < len(output_lines) and output_lines[i].startswith(prefix):
            info_str = output_lines[i][prefix_len:]
            info = info_cls(info_str)
            tracks.append(info)
            i += 1
        return (i, tracks)

    def parse_scan_output(self, input):
        lines = input.splitlines()
        i = 0
        while i < len(lines):
            if lines[i] == "  + audio tracks:":
                logging.info("Found HandBrake audio track info")
                logging.info("Line: %s" % (lines[i]))
                i, hb_audio_tracks = HandBrake().parse_handbrake_track_info(lines, i, HandBrakeAudioInfo)
                logging.info("HandBrake: %d audio track(s)", len(hb_audio_tracks))
                # continue
            i += 1
        return True

    def scan_file(self, handbrake_exe, filename):
        logging.info("Using Handbrake exe: %s" % (handbrake_exe))
        logging.info("Checking on file: %s" % (filename))
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
            logging.info(message_format, file_path)
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
