from config import Global
from difflib import SequenceMatcher
import logging
from logger import Logger

Logger()


class Snapshot(object):
    def __init__(self, client):
        self.client = client

    def find(self, account_id, env):
        '''
            find_snapshots function
        '''
        logging.critical("*** Retrieving snapshots")
        count_deleted = 0
        my_snapshots = sorted(
            self.client.describe_snapshots(
                Filters=[{
                    'Name': 'owner-id',
                    'Values': [account_id]
                    # }, {
                    #     'Name': 'tag:Environment',
                    #     'Values': [env]
                }]
            )['Snapshots'],
            key=lambda x: (
                x['VolumeId'],
                x['StartTime']
            ),
            reverse=True
        )
        for item in my_snapshots:
            method = "undefined"
            try:
                if Global.snapshot_existing[item['VolumeId']]:
                    logging.error("Found existing key for in snapshot_existing for %s" % (item['VolumeId']))
                    pass
            except Exception:
                logging.error("\tInitializing empty key/val for %s" % (item['VolumeId']))
                Global.snapshot_existing[item['VolumeId']] = {'snapshots': []}
            try:
                Global.volume_snapshot_count[item['VolumeId']] = {'count': Global.volume_snapshot_count[item['VolumeId']]['count'] + 1}
            except:
                Global.volume_snapshot_count[item['VolumeId']] = {'count': 1}
            epoch = int(item['StartTime'].strftime("%s"))
            diff = Global.current_time - epoch
            age = diff / Global.full_day
            snap_timestamp = "null"
            snap_persist = False
            try:
                for t in item['Tags']:
                    if t['Key'] == "BuildMethod":
                        method = t['Value']
                    if t['Key'] == "Timestamp":
                        snap_timestamp = t['Value']
                    if t['Key'] == "Persist":
                        snap_persist = t['Value']
            except:
                pass
            match_ratio = SequenceMatcher(
                lambda item:
                item == " ",
                "Created by CreateImage(i-",
                item['Description']
            ).ratio()
            if match_ratio < 0.53 or match_ratio > 0.54:
                # not a snapshot created by an ami
                # if age > args.retention and method != "Packer":
                if method != "Packer":
                    count_deleted = count_deleted + 1
                    try:
                        logging.debug("\t*** appending %s to  snapshot_exsting[ %s ]" % (item['SnapshotId'], item['VolumeId']))
                        Global.snapshot_existing[item['VolumeId']]['snapshots'].append(item['SnapshotId'])
                    except Exception:
                        logging.debug("*** Problem appending %s to  snapshot_exsting[ %s ]" % (item['SnapshotId'], item['VolumeId']))
                        pass
                    Global.snapshot_data[item['SnapshotId']] = {
                        'id': item['SnapshotId'],
                        'volume_id': item['VolumeId'],
                        'description': item['Description'],
                        'date': item['StartTime'],
                        'ratio': match_ratio,
                        'age': age,
                        'method': method,
                        'persist': snap_persist,
                        'timestamp': snap_timestamp,
                        'snap_count': Global.volume_snapshot_count[item['VolumeId']]['count']
                    }
            else:
                # snapshot created by an AMI (generically, don't delete these, except in the case of clean-images)
                Global.image_snapshot[item['SnapshotId']] = {
                    'id': item['SnapshotId'],
                    'volume_id': item['VolumeId'],
                    'description': item['Description'],
                    'date': item['StartTime'],
                    'ratio': match_ratio,
                    'age': age,
                    'method': method,
                    'persist': snap_persist,
                    'timestamp': snap_timestamp,
                    'snap_count': Global.volume_snapshot_count[item['VolumeId']]['count']
                }
        logging.critical("\tTotal snapshots: %i" % (len(my_snapshots)))
        logging.critical("\tTotal snapshots to retain: %i" % (len(my_snapshots) - len(Global.snapshot_data)))
        logging.critical("\tTotal snapshots tagged for rotation: %i" % (len(Global.snapshot_data)))
        return True

    def create(self, region, volume_id, description, old_description, persist):
        '''
            Create snapshot of volume
        '''
        try:
            if Global.instance_data[Global.all_volumes[volume_id]['instance_id']]['environment']:
                if Global.instance_data[Global.all_volumes[volume_id]['instance_id']]['state'] == "running":
                    if not Global.dry_run:
                        logging.critical("\tCreating Snapshot of %s with Description: %s " % (volume_id, description))
                        logging.error("\tCreating tags:")
                        logging.error("\t\tName: %s" % (description))
                        logging.error("\t\tVolume: %s" % (volume_id))
                        logging.error("\t\tDepartpment: %s" % ("ops"))
                        logging.error("\t\tInstanceId: %s" % (Global.all_volumes[volume_id]['instance_id']))
                        logging.error("\t\tEnvironment: %s" % (Global.instance_data[Global.all_volumes[volume_id]['instance_id']]['environment']))
                        logging.error("\t\tRegion: %s" % (region))
                        logging.error("\t\tApplication: %s" % ("shared"))
                        logging.error("\t\tRole: %s" % ("ec2"))
                        logging.error("\t\tService: %s" % ("ebs"))
                        logging.error("\t\tPersist: %s" % (persist))
                        logging.error("\t\tCategory: %s" % ("snapshot"))
                        # create_snap = self.client.create_snapshot(
                        #     VolumeId=volume_id,
                        #     Description=description
                        # )
                        # logging.debug("\t Snapshot created: %s" % (create_snap['SnapshotId']))
                        # self.client.create_tags(
                        #     Resources=[create_snap['SnapshotId']],
                        #     Tags=[{
                        #         'Key': 'Name',
                        #         'Value': description
                        #     }, {
                        #         'Key': 'Volume',
                        #         'Value': volume_id
                        #     }, {
                        #         'Key': 'Department',
                        #         'Value': 'Ops'
                        #     }, {
                        #         'Key': 'Instance',
                        #         'Value': Global.all_volumes[volume_id]['instance_id']
                        #     }, {
                        #         'Key': 'Environment',
                        #         'Value': Global.instance_data[Global.all_volumes[volume_id]['instance_id']]['environment']
                        #     }, {
                        #         'Key': 'Region',
                        #         'Value': region
                        #     }, {
                        #         'Key': 'Application',
                        #         'Value': 'shared'
                        #     }, {
                        #         'Key': 'Role',
                        #         'Value': 'ebs'
                        #     }, {
                        #         'Key': 'Service',
                        #         'Value': 'ec2'
                        #     }, {
                        #         'Key': 'Category',
                        #         'Value': 'snapshot'
                        #     }]
                        # )
                        # logging.critical("\t\t Snapshot %s tags created" % (create_snap['SnapshotId']))
                    else:
                        logging.critical("\t(dry-run) Creating Snapshot of %s with Description: %s " % (volume_id, description))

                    return 1
        except:
            pass
        return 0

    def delete(self, snapshot_id, referrer):
        '''
            delete_snapshot
        '''
        if not Global.dry_run:
            logging.critical("\tDeleting snapshot %s (count:%s :: persist:%s)" % (snapshot_id, Global.volume_snapshot_count[Global.snapshot_data[snapshot_id]['volume_id']]['count'], Global.snapshot_data[snapshot_id]['persist']))
            Global.volume_snapshot_count[Global.snapshot_data[snapshot_id]['volume_id']] = {'count': Global.volume_snapshot_count[Global.snapshot_data[snapshot_id]['volume_id']]['count'] - 1}
            # self.client.delete_snapshot(
            #     # DryRun=True,
            #     SnapshotId=snapshot_id
            # )
        else:
            logging.critical("\t (dry-run) Deleting snapshot %s (count:%s :: persist:%s)" % (snapshot_id, Global.volume_snapshot_count[Global.snapshot_data[snapshot_id]['volume_id']]['count'], Global.snapshot_data[snapshot_id]['persist']))
        return 1
