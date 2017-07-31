import argparse
# from config import Global


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
        parser.add_argument(
            '--type',
            choices=[
                "clean-ami",
                "clean-snapshot",
                "clean-snapshots",
                "clean-volume",
                "clean-volumes",
                "clean",
                "clean-images",
                "create-snapshot",
                "create-snapshots",
                "all"
            ],
            nargs='?',
            metavar='',
            default="all",
            help="type",
            # required=True
        )
        parser.add_argument(
            '--region',
            choices=[
                "us-east-1",
                "us-west-1",
                "us-west-2",
                "ap-southeast-1"
                # etc
            ],
            nargs='?',
            metavar='',
            default="us-west-2",
            help="region",
            # required=True
        )
        parser.add_argument(
            '--account_id',
            nargs='?',
            metavar='',
            default="",
            # required=True,
            help="account_id"
        )
        parser.add_argument(
            '-v',
            dest='verbose',
            nargs='?'
        )
        parser.add_argument(
            '--volume',
            nargs='?',
            default="",
            help="VolumeID"
        )
        parser.add_argument(
            '--instance',
            nargs='?',
            default="",
            help="InstanceID"
        )
        parser.add_argument(
            '--retention',
            nargs='?',
            default=7,
            type=int,
            help="Retention"
        )
        parser.add_argument(
            '--rotation',
            nargs='?',
            default=7,
            type=int,
            help="Rotation"
        )
        parser.add_argument(
            '--hourly',
            action='store_true',
            help="Hourly"
        )
        parser.add_argument(
            '--persist',
            action='store_true',
            help="Persist"
        )
        parser.add_argument(
            '--env',
            choices=[
                "dev",
                "staging",
                "stg",
                "production",
                "prod",
                "prd"
            ],
            nargs='?',
            metavar='',
            default="*",
            help="Environment"
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="DryRun"
        )
        self.args = parser.parse_args()

        if not self.args.type:
            print parser.print_help()
            exit(3)

    def __repr__(self):
        return repr((self.args))
