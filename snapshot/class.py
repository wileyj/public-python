from aws_conn import conn
from difflib import SequenceMatcher
from datetime import datetime, timedelta
import time
import argparse
import logging
from logger import Logger
from config import Global
from args import Args
from instance import Instance
# import sys

Logger()
args = Args().args

if __name__ == "__main__":
    # args.dry_run = True
    if args.env == "prod" or args.env == "prd":
        args.env = "production"
    if args.env == "stg":
        args.env = "staging"
    Logging().configure(args.verbose)
    # __all__ = ('snapshot', 'Logging')
    __all__ = ('Logging')
    logging = logging.getLogger(__name__)

    if args.volume and args.instance:
        print "false. only one option is allowed"
        exit(1)
    if args.volume or args.instance:
        print "Defaulting to type 'create-snapshot' with inclusiong of arg: %s %s" % (args.instance, args.volume)
        args.type = "create-snapshot"
    logging.debug("")
    logging.debug("*** Timing ***")
    logging.debug("\tCurrent time: %i" % (Global.current_time))
    logging.debug("\tRetention: %i" % (args.retention))
    logging.debug("\tFull day in seconds: %i" % (Global.full_day))
    logging.debug("\tToday: %s" % (str(Global.today)))
    logging.debug("\tTomorrow: %s" % (str(Global.tomorrow)))
    logging.debug("\tYesterday: %s" % (str(Global.yesterday)))
    logging.debug("\t2 Weeks Ago: %s" % (str(Global.two_weeks)))
    logging.debug("\t4 Weeks Ago: %s" % (str(Global.four_weeks)))
    logging.debug("\t30 Days Ago: %s" % (str(Global.thirty_days)))
    logging.debug("\tRetention Time: %s" % (str(Global.retention_day)))
    logging.debug("\tStart Date: %s" % (str(Global.start_date)))
    logging.debug("\tShort Date: %s" % (Global.short_date))
    logging.debug("\tShort Hour: %s" % (Global.short_hour))
    logging.debug("")
    logging.debug("*** Defined Args ***")
    logging.debug("\targs.verbose: %s" % (args.verbose))
    logging.debug("\targs.type: %s" % (args.type))
    logging.debug("\targs.env: %s" % (args.env))
    logging.debug("\targs.volume: %s" % (args.volume))
    logging.debug("\targs.instance: %s" % (args.instance))
    logging.debug("\targs.retention: %s" % (args.retention))
    logging.debug("\targs.dry_run: %s" % (args.dry_run))
    logging.debug("\targs.region: %s" % (args.region))
    logging.debug("\targs.account_id: %s" % (args.account_id))
    logging.debug("\targs.rotation: %s" % (args.rotation))
    logging.debug("\targs.hourly: %s" % (args.hourly))
    logging.debug("\targs.persist: %s" % (args.persist))

    Instance().find()
    find_volumes()
    if args.type != "create-snapshot" or args.type != "create-snapshots":
        find_snapshots()
    if not args.volume and not args.instance:
        if args.type != "clean-snapshot" or args.type != "clean-snapshots" or args.type != "clean-volume" or args.type != "clean-volumes":
            find_images()
    if args.type == "all" or args.type == "clean-snapshot" or args.type == "clean-snapshots" or args.type == "clean":
        snapshot_count = 0
        logging.debug("\n\n")
        logging.debug("Ignoring any env flag for cleanup: %s" % (args.env))
        print "*** Cleaning Snapshots ***"
        for snapshot in snapshot_data:
            if volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'] > args.rotation and not snapshot_data[snapshot]['persist'] and not snapshot_data[snapshot]['id'] in image_data:
                logging.debug("")
                logging.debug("snapshot id: %s" % (snapshot_data[snapshot]['id']))
                logging.debug("\tsnap_vol: %s" % (snapshot_data[snapshot]['volume_id']))
                logging.debug("\tsnap_desc: %s" % (snapshot_data[snapshot]['description']))
                logging.debug("\tsnap_date: %s" % (snapshot_data[snapshot]['date']))
                logging.debug("\tsnap_ratio: %s" % (snapshot_data[snapshot]['ratio']))
                logging.debug("\tsnap_age: %s" % (snapshot_data[snapshot]['age']))
                logging.debug("\tsnap_persist: %s" % (snapshot_data[snapshot]['persist']))
                logging.debug("\tsnap_method: %s" % (snapshot_data[snapshot]['method']))
                logging.debug("\tsnap_count: %s" % (snapshot_data[snapshot]['snap_count']))
                logging.debug("\tvolume_snapshot_count: %s" % (volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count']))
                logging.debug("\trotation_scheme: %i" % (args.rotation))
                logging.info("\tDeleting %s - [ snap_count:%s, volume_count:%s, persist: %s ] [ vol: %s ]" % ( snapshot_data[snapshot]['id'], snapshot_data[snapshot]['snap_count'], volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'], snapshot_data[snapshot]['persist'],snapshot_data[snapshot]['volume_id']))
                if snapshot_data[snapshot]['volume_id'] not in all_volumes:
                    logging.debug("\tvol: %s snap: %s snap_count: %s rotate: %i" % (snapshot_data[snapshot]['volume_id'], snapshot_data[snapshot]['id'], volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'], args.rotation))
                    ret_val = delete_snapshot(snapshot_data[snapshot]['id'], '')
                    snapshot_count = snapshot_count + ret_val
                    volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'] = volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'] - ret_val
                else:
                    logging.debug("\tvol: %s snap: %s snap_count: %s rotate: %i" % (snapshot_data[snapshot]['volume_id'], snapshot_data[snapshot]['id'], volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'], args.rotation))
                    ret_val = delete_snapshot(snapshot_data[snapshot]['id'], 'delete_snapshot')
                    snapshot_count = snapshot_count + ret_val
                    volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'] = volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'] - ret_val
            else:
                logging.debug("")
                logging.debug("\tIgnoring deletion of %s - [ snap_count:%s, volume_count:%s, persist: %s ]" % (snapshot_data[snapshot]['id'], snapshot_data[snapshot]['snap_count'], volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'], snapshot_data[snapshot]['persist']))
        print "   *** Total Snapshots Deleted: %s" % (snapshot_count)

    if args.type == "all" or args.type == "clean-volume" or args.type == "clean-volumes" or args.type == "clean":
        volume_count = 0
        logging.debug("\n\n")
        logging.debug("Ignoring any env flag for cleanup: %s" % (args.env))
        print "*** Cleaning Volumes ***"
        print "*** Note: this tags items with tag { 'Delete': 'True' } ***\n"
        for volume in volume_data:
            volume_count = volume_count + 1
            logging.debug("")
            logging.debug("volume_id: %s" % (volume_data[volume]['id']))
            logging.debug("\tvolume_instance_id: %s" % (volume_data[volume]['instance_id']))
            logging.debug("\tvolume_date: %s" % (volume_data[volume]['date']))
        print "   *** Total Volumes To Delete: %s" % (volume_count)

    if args.type == "all" or args.type == "clean-ami" or args.type == "clean" or args.type == "clean-images" :
        image_count = 0
        logging.debug("\n\n")
        logging.debug("Ignoring any env flag for cleanup: %s" % (args.env))
        print "*** Cleaning Images ***"
        for image in image_data:
            image_count = image_count + 1
            logging.debug("")
            logging.debug("ami_id: %s" % (image_data[image]['id']))
            logging.debug("\tami_name: %s" % (image_data[image]['name']))
            logging.debug("\tami_attachment_id: %s" % (image_data[image]['date']))
            logging.debug("\tami_snapshot_id: %s" % (image_data[image]['snapshot_id']))
            logging.debug("\tami_persist: %s" % (image_data[image]['persist']))
            logging.debug("\tami_build_method: %s" % (image_data[image]['build_method']))
            # this is disabled for now until we're sure we want to auto delete AMI's
            # if not image_data[image]['persist']:
            #     for ami_snapshot in image_data[image]['snapshot_id']:
            #         delete_snapshot(ami_snapshot, 'delete_image')
            #     delete_image(image_data[image]['id'], image_data[image]['name'])
        print "   *** Total Images Deregistered: %s" % (image_count)

    if args.type == "all" or args.type == "create-snapshot" or args.type == "create-snapshots":
        snapshot_count = 0
        logging.debug("\n\n")
        print "*** Creating Snapshots ***"
        for s_volume in snapshot_volumes:
            logging.debug("")
            logging.debug("\tsnapshot_volume['volume_id']: %s" % (snapshot_volumes[s_volume]['id']))
            logging.debug("\tsnapshot_volume['instance_id']: %s" % (snapshot_volumes[s_volume]['instance_id']))
            logging.debug("\tsnapshot_volume['date']: %s" % (snapshot_volumes[s_volume]['date']))
            logging.debug("\tsnapshot_volume['desc']: %s" % (snapshot_volumes[s_volume]['desc']))
            logging.debug("\tsnapshot_volume['old_desc']: %s" % (snapshot_volumes[s_volume]['old_desc']))
            logging.debug("\tsnapshot_volume['persist']: %s" % (snapshot_volumes[s_volume]['persist']))
            logging.debug("\tsnapshot_volume['hourly']: %s" % (snapshot_volumes[s_volume]['hourly']))
            snapshot_count = snapshot_count +create_snapshot(snapshot_volumes[s_volume]['id'], snapshot_volumes[s_volume]['desc'], snapshot_volumes[s_volume]['old_desc'], snapshot_volumes[s_volume]['persist'])
        print "   *** Total Volumes to Snapshot: %s" % (snapshot_count)
    exit(0)
