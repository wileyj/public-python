#!/usr/bin/env python
###############################################################
# AniConvert: Batch convert directories of videos using
# HandBrake. Intended to be used on anime and TV series,
# where files downloaded as a batch tend to have the same
# track layout. Can also automatically select a single audio
# and subtitle track based on language preference.
#
# Copyright (c) 2015 Andrew Sun (@crossbowffs)
# Distributed under the MIT license
###############################################################

from __future__ import print_function
import argparse
import collections
import errno
import logging
import os
import re
import subprocess
import sys

###############################################################
# Configuration values, no corresponding command-line args
###############################################################

# Name of the HandBrake CLI binary. Set this to the full path
# of the binary if the script cannot find it automatically.
HANDBRAKE_EXE = "HandBrakeCLI"

# The format string for logging messages
LOGGING_FORMAT = "[%(levelname)s] %(message)s"

# If no output directory is explicitly specified, the output
# files will be placed in a directory with this value appended
# to the name of the input directory.
DEFAULT_OUTPUT_SUFFIX = "-converted"

# Define the arguments to pass to HandBrake.
# Do not define any of the following:
#   -i <input>
#   -o <output>
#   -a <audio track>
#   -s <subtitle track>
#   -w <width>
#   -l <height>
# Obviously, do not define anything that would cause HandBrake
# to not convert the video file either.
HANDBRAKE_ARGS = """
-E ffaac
-B 160
-6 dpl2
-R Auto
-e x264
-q 20.0
--vfr
--audio-copy-mask aac,ac3,dtshd,dts,mp3
--audio-fallback ffaac
--loose-anamorphic
--modulus 2
--x264-preset medium
--h264-profile high
--h264-level 3.1
"""
# --subtitle-burned

INPUT_VIDEO_FORMATS = ["mkv", "mp4", "avi", "mov", "mpg", "MOV", "AVI"]
OUTPUT_VIDEO_FORMAT = "m4v"
AUDIO_LANGUAGES = ["eng"]
SUBTITLE_LANGUAGES = ["eng"]
DUPLICATE_ACTION = "skip"

# The width and height of the output video, in the format
# "1280x720". "1080p" and "720p" are common values and
# translate to 1920x1080 and 1280x720, respectively.
# A value of "auto" is also accepted, and will preserve
# the input video dimensions. On the command line, specify
# as "-d 1280x720", "-d 720p", or "-d auto"
OUTPUT_DIMENSIONS = "auto"

# The minimum severity for an event to be logged. Levels
# from least severe to most servere are "debug", "info",
# "warning", "error", and "critical". On the command line,
# specify as "-l info"
LOGGING_LEVEL = "info"

# By default, if there is only a single track, and it has
# language code "und" (undefined), it will automatically be
# selected. If you do not want this behavior, set this flag
# to true. On the command line, specify as "-u"
MANUAL_UND = False

# Set this to true to search sub-directories within the input
# directory. Files will be output in the correspondingly named
# folder in the destination directory. On the command line,
# specify as "-r"
RECURSIVE_SEARCH = True

###############################################################
# End of configuration values, code begins here
###############################################################

try:
    input = raw_input
except NameError:
    pass


class TrackInfo(object):
    def __init__(self, audio_track, subtitle_track):
        self.audio_track = audio_track
        self.subtitle_track = subtitle_track


class BatchInfo(object):
    def __init__(self, dir_path, track_map):
        self.dir_path = dir_path
        self.track_map = track_map


class FFmpegStreamInfo(object):
    def __init__(self, stream_index, codec_type, codec_name, language_code, metadata):
        self.stream_index = stream_index
        self.codec_type = codec_type
        self.codec_name = codec_name
        self.language_code = language_code
        self.metadata = metadata


class HandBrakeAudioInfo(object):
    pattern1 = re.compile(r"(\d+), (.+) \(iso639-2: ([a-z]{3})\)")
    pattern2 = re.compile(r"(\d+), (.+) \(iso639-2: ([a-z]{3})\), (\d+)Hz, (\d+)bps")

    def __init__(self, info_str):
        match = self.pattern1.match(info_str)
        if not match:
            raise ValueError("Unknown audio track info format: " + repr(info_str))
        self.index = int(match.group(1))
        self.description = match.group(2)
        self.language_code = match.group(3)
        match = self.pattern2.match(info_str)
        if match:
            self.sample_rate = int(match.group(4))
            self.bit_rate = int(match.group(5))
        else:
            self.sample_rate = None
            self.bit_rate = None
        self.title = None

    def __str__(self):
        format_str = (
            "Description: {description}\n"
            "Language code: {language_code}"
        )
        if self.sample_rate:
            format_str += "\nSample rate: {sample_rate}Hz"
        if self.bit_rate:
            format_str += "\nBit rate: {bit_rate}bps"
        return format_str.format(**self.__dict__)

    def __hash__(self):
        return hash((
            self.index,
            self.description,
            self.language_code,
            self.sample_rate,
            self.language_code,
            self.title
        ))

    def __eq__(self, other):
        if not isinstance(other, HandBrakeAudioInfo):
            return False
        return (
            self.index == other.index and
            self.description == other.description and
            self.language_code == other.language_code and
            self.sample_rate == other.sample_rate and
            self.language_code == other.language_code and
            self.title == other.title
        )


class HandBrakeSubtitleInfo(object):
    pattern = re.compile(r"(\d+), (.+) \(iso639-2: ([a-z]{3})\) \((\S+)\)\((\S+)\)")

    def __init__(self, info_str):
        match = self.pattern.match(info_str)
        if not match:
            raise ValueError("Unknown subtitle track info format: " + repr(info_str))
        self.index = int(match.group(1))
        self.language = match.group(2)
        self.language_code = match.group(3)
        self.format = match.group(4)
        self.source = match.group(5)
        self.title = None

    def __str__(self):
        format_str = (
            "Language: {language}\n"
            "Language code: {language_code}\n"
            "Format: {format}\n"
            "Source: {source}"
        )
        return format_str.format(**self.__dict__)

    def __hash__(self):
        return hash((
            self.index,
            self.language,
            self.language_code,
            self.format,
            self.source,
            self.title
        ))

    def __eq__(self, other):
        if not isinstance(other, HandBrakeSubtitleInfo):
            return False
        return (
            self.index == other.index and
            self.language == other.language and
            self.language_code == other.language_code and
            self.format == other.format and
            self.source == other.source and
            self.title == other.title
        )


def print_err(message="", end="\n", flush=False):
    print(message, end=end, file=sys.stderr)
    if flush:
        sys.stderr.flush()


def indent_text(text, prefix):
    if isinstance(prefix, int):
        prefix = " " * prefix
    lines = text.splitlines()
    return "\n".join(prefix + line for line in lines)


def on_walk_error(exception):
    logging.error("Cannot read directory: '%s'", exception.filename)


def get_files_in_dir(path, extensions, recursive):
    extensions = {e.lower() for e in extensions}
    for (dir_path, subdir_names, file_names) in os.walk(path, onerror=on_walk_error):
        filtered_files = []
        for file_name in file_names:
            extension = os.path.splitext(file_name)[1][1:]
            if extension.lower() in extensions:
                filtered_files.append(file_name)
        if len(filtered_files) > 0:
            filtered_files.sort()
            yield (dir_path, filtered_files)
        if recursive:
            subdir_names.sort()
        else:
            del subdir_names[:]


def get_output_dir(base_output_dir, base_input_dir, dir_path):
    relative_path = os.path.relpath(dir_path, base_input_dir)
    if relative_path == ".":
        return base_output_dir
    return os.path.join(base_output_dir, relative_path)


def replace_extension(file_name, new_extension):
    new_file_name = os.path.splitext(file_name)[0] + "." + new_extension
    return new_file_name


def get_simplified_path(base_dir_path, full_path):
    base_parent_dir_path = os.path.dirname(base_dir_path)
    return os.path.relpath(full_path, base_parent_dir_path)


def get_output_path(base_output_dir, base_input_dir, input_path, output_format):
    relative_path = os.path.relpath(input_path, base_input_dir)
    temp_path = os.path.join(base_output_dir, relative_path)
    out_path = os.path.splitext(temp_path)[0] + "." + output_format
    return out_path


def try_create_directory(path):
    try:
        os.makedirs(path, 0o755)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def try_delete_file(path):
    try:
        os.remove(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def run_handbrake_scan(handbrake_path, input_path):
    output = subprocess.check_output([
        handbrake_path,
        "-i", input_path,
        "--scan"
    ], stderr=subprocess.STDOUT)
    return output.decode("utf-8")


def parse_handbrake_track_info(output_lines, start_index, info_cls):
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


def parse_ffmpeg_stream_metadata(output_lines, start_index, metadata_pattern):
    metadata = {}
    i = start_index + 1
    while i < len(output_lines):
        match = metadata_pattern.match(output_lines[i])
        if not match:
            break
        metadata[match.group(1)] = match.group(2)
        i += 1
    return (i, metadata)


def parse_ffmpeg_stream_info(output_lines, start_index):
    stream_pattern = re.compile(r"\s{4}Stream #0\.(\d+)(\(([a-z]{3})\))?: (\S+): (\S+?)")
    metadata_pattern = re.compile(r"\s{6}(\S+)\s*: (.+)")
    audio_streams = []
    subtitle_streams = []
    i = start_index + 1
    while i < len(output_lines) and output_lines[i].startswith("  "):
        match = stream_pattern.match(output_lines[i])
        if not match:
            i += 1
            continue
        stream_index = match.group(1)
        language_code = match.group(3) or "und"
        codec_type = match.group(4)
        codec_name = match.group(5)
        i += 1
        if codec_type == "Audio":
            current_stream = audio_streams
        elif codec_type == "Subtitle":
            current_stream = subtitle_streams
        else:
            continue
        if output_lines[i].startswith("    Metadata:"):
            i, metadata = parse_ffmpeg_stream_metadata(output_lines, i, metadata_pattern)
        else:
            metadata = {}
        info = FFmpegStreamInfo(stream_index, codec_type, codec_name, language_code, metadata)
        current_stream.append(info)
    return (i, audio_streams, subtitle_streams)


def merge_track_titles(hb_tracks, ff_streams):
    if not ff_streams:
        return
    assert len(hb_tracks) == len(ff_streams), "Track count mismatch"
    for hb_track, ff_stream in zip(hb_tracks, ff_streams):
        assert hb_track.language_code == ff_stream.language_code, "Track language code mismatch"
        hb_track.title = ff_stream.metadata.get("title")


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
            i, ff_audio_streams, ff_subtitle_streams = parse_ffmpeg_stream_info(lines, i)
            message_format = "FFmpeg: %d audio track(s), %d subtitle track(s)"
            logging.debug(message_format, len(ff_audio_streams), len(ff_subtitle_streams))
            continue
        if lines[i] == "  + audio tracks:":
            logging.debug("Found HandBrake audio track info")
            i, hb_audio_tracks = parse_handbrake_track_info(lines, i, HandBrakeAudioInfo)
            logging.debug("HandBrake: %d audio track(s)", len(hb_audio_tracks))
            continue
        if lines[i] == "  + subtitle tracks:":
            logging.debug("Found HandBrake subtitle track info")
            i, hb_subtitle_tracks = parse_handbrake_track_info(lines, i, HandBrakeSubtitleInfo)
            logging.debug("HandBrake: %d subtitle track(s)", len(hb_subtitle_tracks))
            continue
        i += 1
    merge_track_titles(hb_audio_tracks, ff_audio_streams)
    merge_track_titles(hb_subtitle_tracks, ff_subtitle_streams)
    return (hb_audio_tracks, hb_subtitle_tracks)


def get_track_info(handbrake_path, input_path):
    scan_output = run_handbrake_scan(handbrake_path, input_path)
    return parse_handbrake_scan_output(scan_output)


def get_track_by_index(track_list, track_index):
    for track in track_list:
        if track.index == track_index:
            return track
    raise IndexError("Invalid track index: " + str(track_index))


def filter_tracks_by_language(track_list, preferred_languages, manual_und):
    for preferred_language_code in preferred_languages:
        preferred_language_code = preferred_language_code.lower()
        if preferred_language_code == "none":
            return None
        und_count = 0
        filtered_tracks = []
        for track in track_list:
            if track.language_code == preferred_language_code:
                filtered_tracks.append(track)
            elif track.language_code == "und":
                und_count += 1
                filtered_tracks.append(track)
        if len(filtered_tracks) - und_count >= 1:
            return filtered_tracks
        elif len(track_list) == und_count:
            if und_count == 1 and not manual_und:
                return track_list
            return []
    return []


def print_track_list(track_list, file_name, track_type):
    track_type = track_type.capitalize()
    print_err("+ Video: '{0}'".format(file_name))
    for track in track_list:
        message_format = "   + [{1}] {0} track: {2}"
        print_err(message_format.format(track_type, track.index, track.title or ""))
        print_err(indent_text(str(track), "      + "))


def prompt_select_track(track_list, filtered_track_list, file_name, track_type):
    print_err("Please select {0} track:".format(track_type))
    print_track_list(filtered_track_list, file_name, track_type)
    prompt_format = "Choose a {0} track # (type 'all' to view all choices): "
    alt_prompt_format = "Choose a {0} track # (type 'none' for no track): "
    if len(track_list) == len(filtered_track_list):
        prompt_format = alt_prompt_format
    while True:
        print_err(prompt_format.format(track_type), end="")
        try:
            input_str = input().lower()
        except KeyboardInterrupt:
            print_err(flush=True)
            raise
        if input_str == "all":
            print_track_list(track_list, file_name, track_type)
            prompt_format = alt_prompt_format
            continue
        if input_str == "none":
            return None
        try:
            track_index = int(input_str)
        except ValueError:
            print_err("Enter a valid number!")
            continue
        try:
            return get_track_by_index(track_list, track_index)
        except IndexError:
            print_err("Enter a valid index!")


def prompt_overwrite_file(file_name):
    print_err("The destination file already exists: '{0}'".format(file_name))
    while True:
        print_err("Do you want to overwrite it? (y/n): ", end="")
        try:
            input_str = input().lower()
        except KeyboardInterrupt:
            print_err(flush=True)
            raise
        if input_str == "y":
            return True
        elif input_str == "n":
            return False
        else:
            print_err("Enter either 'y' or 'n'!")


def select_best_track(track_list, preferred_languages, manual_und, file_name, track_type):
    if len(track_list) == 0:
        logging.info("No %s tracks found", track_type)
        return None
    filtered_tracks = filter_tracks_by_language(track_list, preferred_languages, manual_und)
    if filtered_tracks is None:
        logging.info("Matched 'none' language, discarding %s track", track_type)
        return None
    if len(filtered_tracks) == 1:
        track = filtered_tracks[0]
        message_format = "Automatically selected %s track #%d with language '%s'"
        logging.info(message_format, track_type, track.index, track.language_code)
        return track
    else:
        if len(filtered_tracks) == 0:
            filtered_tracks = track_list
            message_format = "Failed to find any %s tracks that match language list: %s"
        else:
            message_format = "More than one %s track matches language list: %s"
        logging.info(message_format, track_type, preferred_languages)
        track = prompt_select_track(track_list, filtered_tracks, file_name, track_type)
        if track:
            message_format = "User selected %s track #%d with language '%s'"
            logging.info(message_format, track_type, track.index, track.language_code)
        else:
            logging.info("User discarded %s track", track_type)
        return track


def select_best_track_cached(selected_track_map, track_list, preferred_languages, manual_und, file_name, track_type):
    track_set = tuple(track_list)
    try:
        track = selected_track_map[track_set]
    except KeyError:
        track = select_best_track(track_list, preferred_languages, manual_und, file_name, track_type)
        selected_track_map[track_set] = track
    else:
        track_type = track_type.capitalize()
        message_format = "%s track layout already seen, "
        if track:
            message_format += "selected #%d with language '%s'"
            logging.debug(message_format, track_type, track.index, track.language_code)
        else:
            message_format += "no track selected"
            logging.debug(message_format, track_type)
    return track


def process_handbrake_output(process):
    pattern1 = re.compile(r"Encoding: task \d+ of \d+, (\d+\.\d\d) %")
    pattern2 = re.compile(
        r"Encoding: task \d+ of \d+, (\d+\.\d\d) % "
        r"\((\d+\.\d\d) fps, avg (\d+\.\d\d) fps, ETA (\d\dh\d\dm\d\ds)\)")
    percent_complete = None
    current_fps = None
    average_fps = None
    estimated_time = None
    prev_message = ""
    format_str = "Progress: {percent:.2f}% done"
    long_format_str = format_str + " (FPS: {fps:.2f}, average FPS: {avg_fps:.2f}, ETA: {eta})"
    try:
        while True:
            output = process.stdout.readline()
            if len(output) == 0:
                break
            output = output.rstrip()
            match = pattern1.match(output)
            if not match:
                continue
            percent_complete = float(match.group(1))
            match = pattern2.match(output)
            if match:
                format_str = long_format_str
                current_fps = float(match.group(2))
                average_fps = float(match.group(3))
                estimated_time = match.group(4)
            message = format_str.format(
                percent=percent_complete,
                fps=current_fps,
                avg_fps=average_fps,
                eta=estimated_time)
            print_err(message, end="")
            blank_count = max(len(prev_message) - len(message), 0)
            print_err(" " * blank_count, end="\r")
            prev_message = message
    finally:
        print_err(flush=True)


def run_handbrake(arg_list):
    logging.debug("HandBrake args: '%s'", subprocess.list2cmdline(arg_list))
    process = subprocess.Popen(
        arg_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True)
    try:
        process_handbrake_output(process)
    except:
        process.kill()
        process.wait()
        raise
    retcode = process.wait()
    if retcode != 0:
        raise subprocess.CalledProcessError(retcode, arg_list)


def get_handbrake_args(handbrake_path, input_path, output_path, audio_track, subtitle_track, video_dimensions):
    args = HANDBRAKE_ARGS.replace("\n", " ").strip().split()
    args += ["-i", input_path]
    args += ["-o", output_path]
    if audio_track:
        args += ["-a", str(audio_track.index)]
    else:
        args += ["-a", "none"]
    if subtitle_track:
        args += ["-s", str(subtitle_track.index)]
    if video_dimensions != "auto":
        args += ["-w", str(video_dimensions[0])]
        args += ["-l", str(video_dimensions[1])]
    return [handbrake_path] + args


def check_handbrake_executable(file_path):
    if not os.path.isfile(file_path):
        return False
    message_format = "Found HandBrakeCLI binary at '%s'"
    if not os.access(file_path, os.X_OK):
        message_format += ", but it is not executable"
        logging.warning(message_format, file_path)
        return False
    logging.info(message_format, file_path)
    return True


def find_handbrake_executable_in_path(name):
    if os.name == "nt" and not name.lower().endswith(".exe"):
        name += ".exe"
    path_env = os.environ.get("PATH", os.defpath)
    path_env_split = path_env.split(os.pathsep)
    path_env_split.insert(0, os.path.abspath(os.path.dirname(__file__)))
    for dir_path in path_env_split:
        file_path = os.path.join(dir_path, name)
        if check_handbrake_executable(file_path):
            return file_path
    return None


def find_handbrake_executable():
    name = HANDBRAKE_EXE
    if os.path.dirname(name):
        logging.info("Full path to HandBrakeCLI binary specified, ignoring PATH")
        if check_handbrake_executable(name):
            return name
    else:
        handbrake_path = find_handbrake_executable_in_path(name)
        if handbrake_path:
            return handbrake_path
    logging.error("Could not find executable HandBrakeCLI binary")
    return None


def check_output_path(args, output_path):
    simp_output_path = get_simplified_path(args.output_dir, output_path)
    if not os.path.exists(output_path):
        return True
    if os.path.isdir(output_path):
        logging.error("Output path '%s' is a directory, skipping file", simp_output_path)
        return False
    if args.duplicate_action == "prompt":
        return prompt_overwrite_file(simp_output_path)
    elif args.duplicate_action == "skip":
        logging.info("Destination file '%s' already exists, skipping", simp_output_path)
        return False
    elif args.duplicate_action == "overwrite":
        logging.info("Destination file '%s' already exists, overwriting", simp_output_path)
        return True


def filter_convertible_files(args, dir_path, file_names):
    output_dir = get_output_dir(args.output_dir, args.input_dir, dir_path)
    try:
        try_create_directory(output_dir)
    except OSError as e:
        logging.error("Error: %s" % (e))
        logging.error("Cannot create output directory: '%s'", output_dir)
        return []
    convertible_files = []
    for file_name in file_names:
        output_file_name = replace_extension(file_name, args.output_format)
        output_path = os.path.join(output_dir, output_file_name)
        if not check_output_path(args, output_path):
            continue
        convertible_files.append(file_name)
    return convertible_files


def get_track_map(args, dir_path, file_names):
    selected_audio_track_map = {}
    selected_subtitle_track_map = {}
    track_map = collections.OrderedDict()
    for file_name in file_names:
        logging.info("Scanning '%s'", file_name)
        file_path = os.path.join(dir_path, file_name)
        try:
            audio_tracks, subtitle_tracks = get_track_info(
                args.handbrake_path, file_path)
        except subprocess.CalledProcessError as e:
            logging.error("Error occurred while scanning '%s': %s", file_name, e)
            continue
        selected_audio_track = select_best_track_cached(
            selected_audio_track_map, audio_tracks,
            args.audio_languages, args.manual_und,
            file_name, "audio")
        selected_subtitle_track = select_best_track_cached(
            selected_subtitle_track_map, subtitle_tracks,
            args.subtitle_languages, args.manual_und,
            file_name, "subtitle")
        track_map[file_name] = TrackInfo(
            selected_audio_track, selected_subtitle_track)
    return track_map


def generate_batch(args, dir_path, file_names):
    simp_dir_path = get_simplified_path(args.input_dir, dir_path)
    logging.info("Scanning videos in '%s'", simp_dir_path)
    convertible_files = filter_convertible_files(args, dir_path, file_names)
    track_map = get_track_map(args, dir_path, convertible_files)
    if len(track_map) == 0:
        logging.warning("No videos in '%s' can be converted", simp_dir_path)
        return None
    return BatchInfo(dir_path, track_map)


def generate_batches(args):
    dir_list = get_files_in_dir(args.input_dir, args.input_formats, args.recursive_search)
    batch_list = []
    found = False
    for dir_path, file_names in dir_list:
        found = True
        batch = generate_batch(args, dir_path, file_names)
        if batch:
            batch_list.append(batch)
    if not found:
        message = "No videos found in input directory"
        if not args.recursive_search:
            message += ", for recursive search specify '-r'"
        logging.info(message)
    return batch_list


def execute_batch(args, batch):
    output_dir = get_output_dir(args.output_dir, args.input_dir, batch.dir_path)
    try_create_directory(output_dir)
    for file_name, track_info in batch.track_map.items():
        output_file_name = replace_extension(file_name, args.output_format)
        input_path = os.path.join(batch.dir_path, file_name)
        output_path = os.path.join(output_dir, output_file_name)
        simp_input_path = get_simplified_path(args.input_dir, input_path)
        handbrake_args = get_handbrake_args(
            args.handbrake_path,
            input_path,
            output_path,
            track_info.audio_track,
            track_info.subtitle_track,
            args.output_dimensions
        )
        logging.info("Converting '%s'", simp_input_path)
        try:
            run_handbrake(handbrake_args)
        except subprocess.CalledProcessError as e:
            logging.error("Error occurred while converting '%s': %s", simp_input_path, e)
            try_delete_file(output_path)
        except:
            logging.info("Conversion aborted, cleaning up temporary files")
            try_delete_file(output_path)
            raise


def sanitize_and_validate_args(args):
    args.input_dir = os.path.abspath(args.input_dir)
    if not args.output_dir:
        args.output_dir = args.input_dir + DEFAULT_OUTPUT_SUFFIX
    args.output_dir = os.path.abspath(args.output_dir)
    if not os.path.exists(args.input_dir):
        logging.error("Input directory does not exist: '%s'", args.input_dir)
        return False
    if os.path.isfile(args.input_dir):
        logging.error("Input directory is a file: '%s'", args.input_dir)
        return False
    if not os.access(args.input_dir, os.R_OK | os.X_OK):
        logging.error("Cannot read from input directory: '%s'", args.input_dir)
        return False
    if os.path.isfile(args.output_dir):
        logging.error("Output directory is a file: '%s'", args.output_dir)
        return False
    if os.path.isdir(args.output_dir) and not os.access(args.output_dir, os.W_OK | os.X_OK):
        logging.error("Cannot write to output directory: '%s'", args.output_dir)
        return False
    if args.input_dir == args.output_dir:
        logging.error("Input and output directories are the same: '%s'", args.input_dir)
        return False
    if args.handbrake_path:
        args.handbrake_path = os.path.abspath(args.handbrake_path)
        if not os.path.isfile(args.handbrake_path):
            logging.error("HandBrakeCLI binary not found: '%s'", args.handbrake_path)
            return False
        if not os.access(args.handbrake_path, os.X_OK):
            logging.error("HandBrakeCLI binary is not executable: '%s'", args.handbrake_path)
            return False
    else:
        args.handbrake_path = find_handbrake_executable()
        if not args.handbrake_path:
            return False
    return True


def arg_error(message):
    raise argparse.ArgumentTypeError(message)


def parse_output_dimensions(value):
    value_lower = value.lower()
    if value_lower == "auto":
        return value_lower
    if value_lower == "1080p":
        return (1920, 1080)
    if value_lower == "720p":
        return (1280, 720)
    match = re.match(r"^(\d+)x(\d+)$", value_lower)
    if not match:
        arg_error("Invalid video dimensions: " + repr(value))
    width = int(match.group(1))
    height = int(match.group(2))
    return (width, height)


def parse_duplicate_action(value):
    value_lower = value.lower()
    if value_lower not in {"prompt", "skip", "overwrite"}:
        arg_error("Invalid duplicate action: " + repr(value))
    return value_lower


def parse_language_list(value):
    language_list = value.split(",")
    for language in language_list:
        language = language.lower()
        if language == "none":
            continue
        elif language == "und":
            arg_error("Do not specify 'und' language, use '-u' flag instead")
        elif not language.isalpha() or len(language) != 3:
            arg_error("Invalid iso639-2 code: " + repr(language))
    return language_list


def parse_logging_level(value):
    level = getattr(logging, value.upper(), None)
    if level is None:
        arg_error("Invalid logging level: " + repr(value))
    return level


def parse_input_formats(value):
    format_list = value.split(",")
    for input_format in format_list:
        if input_format.startswith("."):
            arg_error("Do not specify the leading '.' on input formats")
        if not input_format.isalnum():
            arg_error("Invalid input format: " + repr(input_format))
    return format_list


def parse_output_format(value):
    if value.startswith("."):
        arg_error("Do not specify the leading '.' on output format")
    if value.lower() not in {"mp4", "mkv", "m4v"}:
        arg_error("Invalid output format (only mp4, mkv, and m4v are supported): " + repr(value))
    return value


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_dir"
    )
    parser.add_argument(
        "-o",
        "--output-dir"
    )
    parser.add_argument(
        "-x",
        "--handbrake-path"
    )
    parser.add_argument(
        "-r",
        "--recursive-search",
        action="store_true",
        default=RECURSIVE_SEARCH
    )
    parser.add_argument(
        "-u",
        "--manual-und",
        action="store_true",
        default=MANUAL_UND
    )
    parser.add_argument(
        "-i",
        "--input-formats",
        type=parse_input_formats,
        default=INPUT_VIDEO_FORMATS
    )
    parser.add_argument(
        "-j",
        "--output-format",
        type=parse_output_format,
        default=OUTPUT_VIDEO_FORMAT
    )
    parser.add_argument(
        "-l",
        "--logging-level",
        type=parse_logging_level,
        default=LOGGING_LEVEL
    )
    parser.add_argument(
        "-w",
        "--duplicate-action",
        type=parse_duplicate_action,
        default=DUPLICATE_ACTION
    )
    parser.add_argument(
        "-d",
        "--output-dimensions",
        type=parse_output_dimensions,
        default=OUTPUT_DIMENSIONS
    )
    parser.add_argument(
        "-a",
        "--audio-languages",
        type=parse_language_list,
        default=AUDIO_LANGUAGES
    )
    parser.add_argument(
        "-s",
        "--subtitle-languages",
        type=parse_language_list,
        default=SUBTITLE_LANGUAGES
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(format=LOGGING_FORMAT, level=args.logging_level, stream=sys.stdout)
    if not sanitize_and_validate_args(args):
        return
    batches = generate_batches(args)
    for batch in batches:
        execute_batch(args, batch)
    logging.info("Done!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
