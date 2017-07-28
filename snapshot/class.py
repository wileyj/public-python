from aws_conn import conn
import logging
from logger import Logger
from config import Global
from args import Args
from instance import Instance
from volume import Volume
from snapshot import Snapshot
from image import Image
from datetime import timedelta

# Logger()
# args = Args().args
# ec2_client = conn('ec2', args.region)
# cloudwatch_client = conn('cloudwatch', args.region)

if __name__ == "__main__":
    Logger()
    args = Args().args
    # ec2_client = conn("ec2", args.region)
    ec2_client = conn().ec2(args.region)
    cloudwatch_client = conn().cloudwatch(args.region)

    # cloudwatch_client = conn('cloudwatch', args.region)

    # args.dry_run = True
    if args.env:
        args.env = Global.env_map[args.env]
    # Logger().configure(args.verbose)
    # __all__ = ('snapshot', 'Logging')
    __all__ = ('snapshot')
    logging = logging.getLogger(__name__)

    if args.volume and args.instance:
        print "false. only one option is allowed"
        exit(1)
    if args.volume or args.instance:
        print "Defaulting to type 'create-snapshot' with inclusiong of arg: %s %s" % (args.instance, args.volume)
        args.type = "create-snapshot"
    retention_day = timedelta(days=args.retention)
    start_date = Global.today - retention_day
    logging.critical("*** Timing ***")
    logging.critical("\tCurrent time: %i" % (Global.current_time))
    logging.critical("\tRetention: %i" % (args.retention))
    logging.critical("\tFull day in seconds: %i" % (Global.full_day))
    logging.critical("\tToday: %s" % (str(Global.today)))
    logging.critical("\tTomorrow: %s" % (str(Global.tomorrow)))
    logging.critical("\tYesterday: %s" % (str(Global.yesterday)))
    logging.critical("\t2 Weeks Ago: %s" % (str(Global.two_weeks)))
    logging.critical("\t4 Weeks Ago: %s" % (str(Global.four_weeks)))
    logging.critical("\t30 Days Ago: %s" % (str(Global.thirty_days)))
    logging.critical("\tRetention Time: %s" % (str(retention_day)))
    logging.critical("\tStart Date: %s" % (str(start_date)))
    logging.critical("\tShort Date: %s" % (Global.short_date))
    logging.critical("\tShort Hour: %s" % (Global.short_hour))
    logging.critical("")
    logging.critical("*** Defined Args ***")
    logging.critical("\targs.verbose: %s" % (args.verbose))
    logging.critical("\targs.type: %s" % (args.type))
    logging.critical("\targs.env: %s" % (args.env))
    logging.critical("\targs.volume: %s" % (args.volume))
    logging.critical("\targs.instance: %s" % (args.instance))
    logging.critical("\targs.retention: %s" % (args.retention))
    logging.critical("\targs.dry_run: %s" % (args.dry_run))
    logging.critical("\targs.region: %s" % (args.region))
    logging.critical("\targs.account_id: %s" % (args.account_id))
    logging.critical("\targs.rotation: %s" % (args.rotation))
    logging.critical("\targs.hourly: %s" % (args.hourly))
    logging.critical("\targs.persist: %s" % (args.persist))

    Instance(ec2_client).find(args.env, '')
    exit(0)
    # Volume(ec2_client).find(cloudwatch_client, args.instance, args.volume, args.hourly, args.persist)
    # if args.type != "create-snapshot" or args.type != "create-snapshots":
    #     Snapshot(ec2_client).find(Global.account_id, args.env)
    # if not args.volume and not args.instance:
    #     if args.type != "clean-snapshot" or args.type != "clean-snapshots" or args.type != "clean-volume" or args.type != "clean-volumes":
    #         Image(ec2_client).find(args.env, Global.account_id)
    # if args.type == "all" or args.type == "clean-snapshot" or args.type == "clean-snapshots" or args.type == "clean":
    #     snapshot_count = 0
    #     logging.error("\n\n")
    #     logging.error("Ignoring any env flag for cleanup: %s" % (args.env))
    #     logging.error("*** Cleaning Snapshots ***")
    #     for snapshot in Global.snapshot_data:
    #         if Global.volume_snapshot_count[Global.snapshot_data[snapshot]['volume_id']]['count'] > args.rotation and not Global.snapshot_data[snapshot]['persist'] and not Global.snapshot_data[snapshot]['id'] in Global.image_data:
    #             logging.critical("")
    #             logging.error("snapshot id: %s" % (Global.snapshot_data[snapshot]['id']))
    #             logging.error("\tsnap_vol: %s" % (Global.snapshot_data[snapshot]['volume_id']))
    #             logging.error("\tsnap_desc: %s" % (Global.snapshot_data[snapshot]['description']))
    #             logging.error("\tsnap_date: %s" % (Global.snapshot_data[snapshot]['date']))
    #             logging.error("\tsnap_ratio: %s" % (Global.snapshot_data[snapshot]['ratio']))
    #             logging.error("\tsnap_age: %s" % (Global.snapshot_data[snapshot]['age']))
    #             logging.error("\tsnap_persist: %s" % (Global.snapshot_data[snapshot]['persist']))
    #             logging.error("\tsnap_method: %s" % (Global.snapshot_data[snapshot]['method']))
    #             logging.error("\tsnap_count: %s" % (Global.snapshot_data[snapshot]['snap_count']))
    #             logging.error("\tvolume_snapshot_count: %s" % (Global.volume_snapshot_count[Global.snapshot_data[snapshot]['volume_id']]['count']))
    #             logging.error("\trotation_scheme: %i" % (args.rotation))
    #             logging.critical("\tDeleting %s - [ snap_count:%s, volume_count:%s, persist: %s ] [ vol: %s ]" % (Global.snapshot_data[snapshot]['id'], Global.snapshot_data[snapshot]['snap_count'], Global.volume_snapshot_count[Global.snapshot_data[snapshot]['volume_id']]['count'], Global.snapshot_data[snapshot]['persist'], Global.snapshot_data[snapshot]['volume_id']))
    #             if Global.snapshot_data[snapshot]['volume_id'] not in Global.all_volumes:
    #                 logging.debug("\tvol: %s snap: %s snap_count: %s rotate: %i" % (Global.snapshot_data[snapshot]['volume_id'], Global.snapshot_data[snapshot]['id'], Global.volume_snapshot_count[Global.snapshot_data[snapshot]['volume_id']]['count'], args.rotation))
    #                 ret_val = Snapshot().delete(Global.snapshot_data[snapshot]['id'], '')
    #                 Global.snapshot_count = Global.snapshot_count + ret_val
    #                 Global.volume_snapshot_count[Global.snapshot_data[snapshot]['volume_id']]['count'] = Global.volume_snapshot_count[Global.snapshot_data[snapshot]['volume_id']]['count'] - ret_val
    #             else:
    #                 logging.debug("\tvol: %s snap: %s snap_count: %s rotate: %i" % (Global.snapshot_data[snapshot]['volume_id'], Global.snapshot_data[snapshot]['id'], Global.volume_snapshot_count[Global.snapshot_data[snapshot]['volume_id']]['count'], args.rotation))
    #                 ret_val = Snapshot().delete(Global.snapshot_data[snapshot]['id'], 'delete_snapshot')
    #                 Global.snapshot_count = Global.snapshot_count + ret_val
    #                 Global.volume_snapshot_count[Global.snapshot_data[snapshot]['volume_id']]['count'] = Global.volume_snapshot_count[Global.snapshot_data[snapshot]['volume_id']]['count'] - ret_val
    #         else:
    #             logging.critical("")
    #             logging.critical("\tIgnoring deletion of %s - [ snap_count:%s, volume_count:%s, persist: %s ]" % (Global.snapshot_data[snapshot]['id'], Global.snapshot_data[snapshot]['snap_count'], Global.volume_snapshot_count[Global.snapshot_data[snapshot]['volume_id']]['count'], Global.snapshot_data[snapshot]['persist']))
    #     logging.critical("   *** Total Snapshots Deleted: %s" % (snapshot_count))
    #
    # if args.type == "all" or args.type == "clean-volume" or args.type == "clean-volumes" or args.type == "clean":
    #     volume_count = 0
    #     logging.error("\n\n")
    #     logging.error("Ignoring any env flag for cleanup: %s" % (args.env))
    #     logging.critical("*** Cleaning Volumes ***")
    #     logging.critical("*** Note: this tags items with tag { 'Delete': 'True' } ***\n")
    #     for volume in Global.volume_data:
    #         volume_count = volume_count + 1
    #         logging.critical("")
    #         logging.critical("volume_id: %s" % (Global.volume_data[volume]['id']))
    #         logging.critical("\tvolume_instance_id: %s" % (Global.volume_data[volume]['instance_id']))
    #         logging.critical("\tvolume_date: %s" % (Global.volume_data[volume]['date']))
    #     logging.critical("   *** Total Volumes To Delete: %s" % (volume_count))
    #
    # if args.type == "all" or args.type == "clean-ami" or args.type == "clean" or args.type == "clean-images":
    #     image_count = 0
    #     logging.error("\n\n")
    #     logging.error("Ignoring any env flag for cleanup: %s" % (args.env))
    #     logging.critical("*** Cleaning Images ***")
    #     for image in Global.image_data:
    #         image_count = image_count + 1
    #         logging.critical("")
    #         logging.critical("ami_id: %s" % (Global.image_data[image]['id']))
    #         logging.critical("\tami_name: %s" % (Global.image_data[image]['name']))
    #         logging.critical("\tami_attachment_id: %s" % (Global.image_data[image]['date']))
    #         logging.critical("\tami_snapshot_id: %s" % (Global.image_data[image]['snapshot_id']))
    #         logging.critical("\tami_persist: %s" % (Global.image_data[image]['persist']))
    #         logging.critical("\tami_build_method: %s" % (Global.image_data[image]['build_method']))
    #         # this is disabled for now until we're sure we want to auto delete AMI's
    #         # if not image_data[image]['persist']:
    #         #     for ami_snapshot in image_data[image]['snapshot_id']:
    #         #         delete_snapshot(ami_snapshot, 'delete_image')
    #         #     delete_image(image_data[image]['id'], image_data[image]['name'])
    #     logging.critical("   *** Total Images Deregistered: %s" % (image_count))
    #
    # if args.type == "all" or args.type == "create-snapshot" or args.type == "create-snapshots":
    #     snapshot_count = 0
    #     logging.error("\n\n")
    #     logging.error("*** Creating Snapshots ***")
    #     for s_volume in Global.snapshot_volumes:
    #         logging.critical("")
    #         logging.critical("\tsnapshot_volume['volume_id']: %s" % (Global.snapshot_volumes[s_volume]['id']))
    #         logging.critical("\tsnapshot_volume['instance_id']: %s" % (Global.snapshot_volumes[s_volume]['instance_id']))
    #         logging.critical("\tsnapshot_volume['date']: %s" % (Global.snapshot_volumes[s_volume]['date']))
    #         logging.critical("\tsnapshot_volume['desc']: %s" % (Global.snapshot_volumes[s_volume]['desc']))
    #         logging.critical("\tsnapshot_volume['old_desc']: %s" % (Global.snapshot_volumes[s_volume]['old_desc']))
    #         logging.critical("\tsnapshot_volume['persist']: %s" % (Global.snapshot_volumes[s_volume]['persist']))
    #         logging.critical("\tsnapshot_volume['hourly']: %s" % (Global.snapshot_volumes[s_volume]['hourly']))
    #         snapshot_count = snapshot_count + Snapshot(ec2_client).create(Global.snapshot_volumes[s_volume]['id'], Global.snapshot_volumes[s_volume]['desc'], Global.snapshot_volumes[s_volume]['old_desc'], Global.snapshot_volumes[s_volume]['persist'])
    #     logging.critical("   *** Total Volumes to Snapshot: %s" % (snapshot_count))
    # exit(0)
