import argparse


class VAction(argparse.Action):
    '''
        Class to configure verbosity level
    '''
    def __call__(self, argparser, cmdargs, values, option_string=None):
        if values is None:
            values = '1'
        try:
            values = int(values)
        except ValueError:
            values = values.count('v') + 1
        setattr(cmdargs, self.dest, values)

class Args:
    def __init__(self):
        parser = argparse.ArgumentParser()
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
