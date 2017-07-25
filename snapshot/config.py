from args import Args
import time
from datetime import datetime, timedelta

args = Args().args


class Globals(object):
    default_rotation = 7
    default_retention = 7
    volume_metric_mininum = 100
    instance_data = {}
    image_data = {}
    map_images = {}
    image_snapshot = {}
    ignored_images = []
    snapshot_data = {}
    snapshot_existing = {}
    volume_data = {}
    all_volumes = {}
    snapshot_volumes = {}
    volume_snapshot_count = {}
    region = args.region
    current_time = int(round(time.time()))
    full_day = 86400
    time_diff = args.retention * full_day
    today = datetime.now()
    tomorrow = datetime.now() + timedelta(days=1)
    yesterday = datetime.now() - timedelta(days=1)
    two_weeks = datetime.now() - timedelta(days=14)
    four_weeks = datetime.now() - timedelta(days=28)
    thirty_days = datetime.now() - timedelta(days=30)
    retention_day = timedelta(days=Args().retention)
    start_date = today - retention_day
    short_date = str('{:04d}'.format(today.year)) + str('{:02d}'.format(today.month)) + str('{:02d}'.format(today.day))
    short_hour = str('{:04d}'.format(today.year)) + str('{:02d}'.format(today.month)) + str('{:02d}'.format(today.day)) + "_" + str(current_time)
    dry_run = args.dry_run
