import sys
import logging
from logger import Logger
from config import Global
from args import Args
from dir_watcher import Dir

args = Args().args
Logger()


class main():
    def __init__():
        logging.basicConfig(
            format=Global.LOGGING_FORMAT,
            level=args.logging_level,
            stream=sys.stdout
        )
        batches = Dir().generate_batches(args)
        for batch in batches:
            Dir().execute_batch(args, batch)
        logging.info("Done!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
