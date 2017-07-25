import logging
import os
from args import Args


class Logger:
    def __init__(self):
        args = Args().args
        if args.verbose > 3:
            log_format = '%(asctime)-4s [%(levelname)-s] %(filename)-s %(module)-s:%(funcName)-4s(%(lineno)-s) - %(message)-4s'
            # log_format = '[DEBUG] - %(lineno)-4s %(asctime)-15s  %(message)-4s'
            logging.basicConfig(level=logging.DEBUG, format=log_format)
            os.environ["PACKER_LOG"] = "error"
        elif args.verbose == 3:
            log_format = '%(asctime)-4s [%(levelname)-s] %(filename)-s %(funcName)-4s(%(lineno)-s) - %(message)-4s'
            # log_format = '[INFO]  - %(lineno)-4s %(message)-4s'
            logging.basicConfig(level=logging.INFO, format=log_format)
            os.environ["PACKER_LOG"] = "error"
        elif args.verbose == 2:
            log_format = '[%(levelname)-s] %(funcName)-4s(%(lineno)-s) - %(message)-4s'
            logging.basicConfig(level=logging.WARNING, format=log_format)
            os.environ["PACKER_LOG"] = "error"
        elif args.verbose == 1:
            log_format = '[%(levelname)-s] - %(message)-4s'
            logging.basicConfig(level=logging.ERROR, format=log_format)
            os.environ["PACKER_LOG"] = "critical"
        else:
            log_format = '%(message)-4s'
            logging.basicConfig(level=logging.CRITICAL, format=log_format)
            os.environ["PACKER_LOG"] = "critical"
