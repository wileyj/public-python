#!/usr/bin/env python
# ported from snapshot.py for use in lambda

# sample test event:
# {
#     "type": "clean-snapshot",
#     "region": "us-east-1",
#     "account_id": "<account_id>",
#     "volume": "",
#     "verbose": "",
#     "instance": "",
#     "retention": 7,
#     "rotation": 7,
#     "hourly": "",
#     "persist": "",
#     "env": "*",
#     "dry_run": "true"
# }

import argparse
import logging
import boto3
import time
import sys
from datetime import datetime, timedelta
from difflib import SequenceMatcher


LOGGER_NAME = None
logger = logging.getLogger()
_log_info       = '[%(levelname)s] %(message)s'
_log_error      = '[%(levelname)s] [ %(asctime)s ] %(message)s'
_log_critical   = '[%(levelname)s] [ %(asctime)s::%(lineno)s ] %(message)s'
_log_debug      = '[%(levelname)s] [ %(asctime)s::%(funcName)s::%(lineno)s ] %(message)s'
logger = logging.getLogger()
for h in logger.handlers:
    logger.removeHandler(h)
h = logging.StreamHandler(sys.stdout)


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
current_time = int(round(time.time()))
full_day = 86400
today = datetime.now()
tomorrow = datetime.now() + timedelta(days=1)
yesterday = datetime.now() - timedelta(days=1)
two_weeks = datetime.now() - timedelta(days=14)
four_weeks = datetime.now() - timedelta(days=28)
thirty_days = datetime.now() - timedelta(days=30)

def find_instances(args):
    """ find_instances function """
    logger.info("*** Retrieving instances")
    client = boto3.client('ec2', region_name=args.region)
    instances_vpc = sorted(
        client.describe_instances(
            Filters=[{
                'Name': 'vpc-id',
                'Values': ['*']
            },{
                'Name': 'instance-state-name',
                'Values': ['running', 'stopped']
            },{
                'Name': 'tag:Environment',
                'Values': [args.env]
            }]
        )['Reservations'],
            key=lambda x: (
                x['Instances'][0]['LaunchTime'],
                x['Instances'][0]['InstanceId']
            ),
            reverse=True
        )
    if not args.instance:
        instances_all = sorted(
            client.describe_instances(
                Filters=[{
                    'Name': 'instance-state-name',
                    'Values': ['running', 'stopped']
                },{
                    'Name': 'tag:Environment',
                    'Values': [args.env]
                }]
            )['Reservations'],
            key=lambda x: (
                x['Instances'][0]['LaunchTime'],
                x['Instances'][0]['InstanceId']
            ),
            reverse=True
        )
    else:
        instances_all = sorted(
            client.describe_instances(
                Filters=[{
                    'Name': 'instance-state-name',
                    'Values': ['running', 'stopped']
                },{
                    'Name': 'instance-id',
                    'Values': [args.instance]
                }]
            )['Reservations'],
            key=lambda x: (
                x['Instances'][0]['LaunchTime'],
                x['Instances'][0]['InstanceId']
            ),
            reverse=True
        )

    try:
        if len(instances_all) < 1:
            if len(args.verbose) >= 2:  logger.error("instances_all returned %i results..." % (len(instances_all)))
    except ValueError as err:
        if len(args.verbose) >= 3:  logger.debug("instances_all size: %i (%s)" % (len(instances_all), err))
        pass
    list_vpc = [item for item in instances_vpc ]
    list_all = [item for item in instances_all ]
    instance_without_vpc = [ item for item in instances_all  if item not in list_vpc ]
    running_count = 0
    stopped_count = 0
    for item in instances_all:
        t_name = ""
        t_env = ""
        t_vpc = ""
        platform = ""
        try:
            for tag in item['Instances'][0]['Tags']:
                if tag['Key'] == "Name":
                    t_name = tag['Value']
                if tag['Key'] == "Environment":
                    t_env = tag['Value']
        except:
            t_name = item['Instances'][0]['InstanceId']
        try:
            t_vpc = item['Instances'][0]['VpcId']
        except LookupError as err:
            if len(args.verbose) >= 2: logger.error("\t Error Finding VpcId for %s (%s)" % (item['Instances'][0]['InstanceId'], err))
            t_vpc = "None"
        try:
            if item['Instances'][0]['Platform']:
                platform = item['Instances'][0]['Platform']
        except LookupError as err:
            if len(args.verbose) >= 2: logger.error("\t Error Finding Platform for %s (%s)" % (item['Instances'][0]['InstanceId'], err))
            platform = "Linux"
        try:
            if item['Instances'][0]['PrivateIpAddress']:
                private_ip_address = item['Instances'][0]['PrivateIpAddress']
        except LookupError as err:
            if len(args.verbose) >= 2: logger.error("\t Error Finding PrivateIPAddress for %s (%s)" % (item['Instances'][0]['InstanceId'], err))
            private_ip_address = "Undefined"
        try:
            if item['Instances'][0]['SubnetId']:
                subnet_id = item['Instances'][0]['SubnetId']
        except LookupError as err:
            if len(args.verbose) >= 2: logger.error("\t Error Finding SubnetId for %s (%s)" % (item['Instances'][0]['InstanceId'], err))
            subnet_id = "Undefined"
        instance_data[item['Instances'][0]['InstanceId']] = {
            'id': item['Instances'][0]['InstanceId'],
            'state': item['Instances'][0]['State']['Name'],
            'type': item['Instances'][0]['InstanceType'],
            'private_dns': item['Instances'][0]['PrivateDnsName'],
            'private_ip': private_ip_address,
            'launch_time': item['Instances'][0]['LaunchTime'],
            'image_id': item['Instances'][0]['ImageId'],
            'platform': platform,
            'subnet_id': subnet_id,
            'virt': item['Instances'][0]['VirtualizationType'],
            'name': t_name,
            'vpc': t_vpc,
            'environment': t_env,
            'volumes': []
        }
        if item['Instances'][0]['State']['Name'] == 'running':
            running_count = running_count + 1
        else:
            stopped_count = stopped_count + 1
            if not args.dry_run:
                client.create_tags(
                    Resources=[item['Instances'][0]['InstanceId']],
                    Tags = [{
                        'Key': 'Delete',
                        'Value': 'True'
                    }]
                )
        for volume in item['Instances'][0]['BlockDeviceMappings']:
            instance_data[item['Instances'][0]['InstanceId']]['volumes'].append(volume['Ebs']['VolumeId'])

        # swap
        try:
            map_images[item['Instances'][0]['ImageId']]['instance_id'].append(item['Instances'][0]['InstanceId'])
            # map_images[item['Instances'][0]['ImageId']] = {
            #     'imaged_id': item['Instances'][0]['ImageId'],
            #     'instance_id': [item['Instances'][0]['InstanceId']],
            # }
        except LookupError as err:
            if len(args.verbose) >= 2: logger.error("Error Appending to map_images, key does not exist: %s" % (err))
            # map_images[item['Instances'][0]['ImageId']]['instance_id'].append(item['Instances'][0]['InstanceId'])
            map_images[item['Instances'][0]['ImageId']] = {
                'imaged_id': item['Instances'][0]['ImageId'],
                'instance_id': [item['Instances'][0]['InstanceId']],
            }
        # end swap

    logger.info("\t Total VPC Instances: %s" % (len(list_vpc)))
    logger.info("\t Total Instances: %s" % (len(list_all)))
    logger.info("\t Total Classic Instances: %i" % (len(instance_without_vpc)))
    logger.info("\t Total Running Instances: %i" % (running_count))
    logger.info("\t Total Stopped Instances: %i" % (stopped_count))
    logger.info("\t Total Mapped Instances: %i" % (len(map_images)))
    logger.info("\t Items in instance_data dict: %i" % (len(instance_data)))
    return True

def find_images(args):
    """ find_images function """
    logger.info("*** Retrieving images")
    client = boto3.client('ec2', region_name=args.region)
    if args.env != "*":
        logger.warning("\tDiscarding env arg for image retrieval")
    count_images = 0
    my_images = sorted(
        client.describe_images(
            Owners=[args.account_id]
        )['Images'],
        key=lambda x: (
            x['Name'],
            x['CreationDate']
        ),
        reverse=True
    )
    for x in my_images:
        count_images = count_images + 1
        # set_buildmethod = False
        set_persist = False
        set_buildmethod = "undefined"
        try:
            for t in x['Tags']:
                if t['Key'] == "Persist":
                    set_persist = t['Value']
                    if len(args.verbose) >= 3: logger.debug("\tFound Persist Tag (%s) in image (%s)" % (set_persist, x['ImageId']))
                if t['Key'] == "BuildMethod":
                    set_buildmethod = t['Value']
        except LookupError as err:
            if len(args.verbose) >= 2: logger.error("\t ** tags for %s not found (%s)" % (x['ImageId'], err))
            set_persist = False
            set_buildmethod = "undefined"
        if set_persist == False:
            ami_snapshot_existing = []
            for index, this in enumerate(x['BlockDeviceMappings'], start=0):
                if 'Ebs' in this and 'SnapshotId' in this['Ebs']:
                    # the following 4 lines make it so that ami snapshots are ignored
                    if len(args.verbose) >= 3: logger.debug("Found AMI snapshot: %s" % (this['Ebs']['SnapshotId']))
                    if this['Ebs']['SnapshotId'] in snapshot_data:
                        logger.warning("\tRemoving AMI snapshot from snapshot_data - %s:%s" % (x['ImageId'], this['Ebs']['SnapshotId']))
                        del snapshot_data[this['Ebs']['SnapshotId']]
                    ami_snapshot_existing.append(this['Ebs']['SnapshotId'])
            if not x['ImageId'] in map_images:
                if len(args.verbose) >= 3: logger.debug("[ INACTIVE ] image: %s ( %s )" % (x['ImageId'], x['Name']))
                image_data[x['ImageId']] = {
                    'id': x['ImageId'],
                    'name': x['Name'],
                    'active': False,
                    'date': x['CreationDate'],
                    'persist': set_persist,
                    'build_method': set_buildmethod,
                    'snapshot_id': ami_snapshot_existing
                }
            else:
                if len(args.verbose) >= 3: logger.debug("[ ACTIVE ]   %s ( %s )" % (x['ImageId'], x['Name']))
    logger.info("\tTotal Images Found: %i" % (count_images))
    logger.info("\tTotal Images tagged for deletion: %i" % (len(image_data)))
    return True

def find_snapshots(args):
    """" find_snapshots function """
    logger.info("*** Retrieving snapshots")
    client = boto3.client('ec2', region_name=args.region)
    count_deleted = 0
    my_snapshots = sorted(
        client.describe_snapshots(
            Filters=[{
                'Name': 'owner-id',
                'Values': [args.account_id]
            # this won't work untill all old snapshots have been removed and/or tagged
            # },{
            #     'Name': 'tag:Environment',
            #     'Values': [args.env]
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
            if snapshot_existing[item['VolumeId']]:
                if len(args.verbose) >= 3: logger.debug("Found existing key for in snapshot_existing for %s" % (item['VolumeId']))
                pass
        except LookupError as err:
            if len(args.verbose) >= 3: logger.debug("\tInitializing empty key/val for %s (%s)" % (item['VolumeId'], err))
            snapshot_existing[item['VolumeId']] = { 'snapshots': [] }
        try:
            volume_snapshot_count[item['VolumeId']] = { 'count': volume_snapshot_count[item['VolumeId']]['count'] + 1 }
        except:
            volume_snapshot_count[item['VolumeId']] = { 'count': 1 }
        epoch = int(item['StartTime'].strftime("%s"))
        diff = current_time - epoch
        age = diff/full_day
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
                    if len(args.verbose) >= 3: logger.debug("\t*** appending %s to  snapshot_exsting[ %s ]" % (item['SnapshotId'], item['VolumeId']))
                    snapshot_existing[item['VolumeId']]['snapshots'].append(item['SnapshotId'])
                except LookupError as err:
                    if len(args.verbose) >= 3: logger.debug("*** Problem appending %s to  snapshot_exsting[ %s ] (%s)" % (item['SnapshotId'], item['VolumeId'], err))
                    pass
                snapshot_data[item['SnapshotId']] = {
                    'id': item['SnapshotId'],
                    'volume_id': item['VolumeId'],
                    'description': item['Description'],
                    'date': item['StartTime'],
                    'ratio': match_ratio,
                    'age': age,
                    'method': method,
                    'persist': snap_persist,
                    'timestamp': snap_timestamp,
                    'snap_count': volume_snapshot_count[item['VolumeId']]['count']
                }
        else:
            # snapshot created by an AMI (generically, don't delete these, except in the case of clean-images)
            image_snapshot[item['SnapshotId']] = {
                'id': item['SnapshotId'],
                'volume_id': item['VolumeId'],
                'description': item['Description'],
                'date': item['StartTime'],
                'ratio': match_ratio,
                'age': age,
                'method': method,
                'persist': snap_persist,
                'timestamp': snap_timestamp,
                'snap_count': volume_snapshot_count[item['VolumeId']]['count']
            }
    logger.info("\tTotal snapshots: %i" % (len(my_snapshots)))
    logger.info("\tTotal snapshots to retain: %i" % (len(my_snapshots) - len(snapshot_data)))
    logger.info("\tTotal snapshots tagged for rotation: %i" % (len(snapshot_data)))
    return True

def find_volumes(args):
    """ find_volumes function """
    logger.info("*** Retrieving volumes")
    if not args.instance and not args.volume:
        client = boto3.client('ec2', region_name=args.region)
        my_volumes = client.describe_volumes()['Volumes']
    else:
        if args.instance:
            my_volumes = sorted(
                client.describe_volumes(
                    Filters=[{
                        'Name': 'volume-id',
                        'Values': instance_data[args.instance]['volumes']
                    }]
                )['Volumes'],
                key=lambda x: (
                    x['VolumeId']
                ),
                reverse=True
            )
        else:
            my_volumes = sorted(
                client.describe_volumes(
                    Filters=[{
                        'Name': 'volume-id',
                        'Values': [args.volume]
                    }]
                )['Volumes'],
                key=lambda x: (
                    x['VolumeId']
                ),
                reverse=True
            )
    for volume in my_volumes:
        tag_delete = False
        try:
            for tag in volume['Tags']:
                if tag['Key'] == 'Delete':
                    tag_delete = tag['Value']
        except:
            pass
        for attached in volume['Attachments']:
            all_volumes[volume['VolumeId']] = {
                'id': volume['VolumeId'],
                'attachment_id': attached['VolumeId'],
                'instance_id': attached['InstanceId'],
                'snapshot_id': volume['SnapshotId'],
                'device': attached['Device'],
                'state': volume['State'],
                'size': volume['Size'],
                'date': volume['CreateTime']
            }
            volume_snapshot_count[attached['VolumeId']] = { 'count': 0 }
            if tag_delete == 'True':
                volume_data[volume['VolumeId']] = {
                    'id': volume['VolumeId'],
                    'attachment_id': attached['VolumeId'],
                    'instance_id': attached['InstanceId'],
                    'snapshot_id': volume['SnapshotId'],
                    'device': attached['Device'],
                    'state': volume['State'],
                    'size': volume['Size'],
                    'date': volume['CreateTime']
                }
            else:
                ##
                ## disable the following conditional to speed up processing when running on lambda
                ## to renable, simply uncomment this condtional, comment line 453, and uncomment the functions being called
                ##
                # if is_candidate(args, volume['VolumeId'], attached['InstanceId'], args.region):
                #     if len(args.verbose) >= 3: logger.debug("\t\tCandidate Volume (%s, %s)" % (attached['InstanceId'] , volume['VolumeId']))
                #     if len(args.verbose) >= 3: logger.debug("\t\tTagging Volume for deletion (%s, %s)" % (attached['InstanceId'], volume['VolumeId']))
                #     volume_data[volume['VolumeId']] = {
                #         'id': volume['VolumeId'],
                #         'attachment_id': attached['VolumeId'],
                #         'instance_id': attached['InstanceId'],
                #         'snapshot_id': volume['SnapshotId'],
                #         'device': attached['Device'],
                #         'state': volume['State'],
                #         'size': volume['Size'],
                #         'date': volume['CreateTime']
                #     }
                #     logger.info("Tagging Volume %s with {'Delete': 'True'}" % (volume['VolumeId']))
                #     if not args.dry_run:
                #         logger.warning("(dry-run) Tagging Volume %s with {'Delete': 'True'}" % (volume['VolumeId']))
                #         client.create_tags(
                #             Resources=[volume['VolumeId']],
                #             Tags = [{
                #                 'Key': 'Delete',
                #                 'Value': 'True'
                #             }]
                #         )
                # else:
                ## start temp conditional
                ## this following line is just here so that the block below doesn't have to be re-indented if volume function is re-enabled
                ## either delete or comment the following 1 line if the above conditional is re-enabled
                if volume['Attachments'] is not None:
                ## end temp conditional
                    if len(volume['Attachments']) > 0:
                        short_date = str('{:04d}'.format(today.year))+str('{:02d}'.format(today.month))+str('{:02d}'.format(today.day))
                        short_hour = str('{:04d}'.format(today.year))+str('{:02d}'.format(today.month))+str('{:02d}'.format(today.day))+"_"+str(current_time)
                        if args.hourly:
                            desc = short_hour
                        else:
                            desc = short_date
                        if args.persist:
                            persist = True
                        else:
                            persist = False
                        # here we flag a volume for backup
                        if attached['InstanceId'] not in instance_data:
                            desc = desc+":"+attached['InstanceId']
                        else:
                            desc = desc+":"+instance_data[attached['InstanceId']]['name'].replace(" - ", "-")
                        desc = desc.replace(")", "")
                        desc = desc.replace("(", "")
                        desc = desc.replace(" ", "-")
                        snapshot_volumes[volume['VolumeId']] = {
                            'id': volume['VolumeId'],
                            'instance_id': attached['InstanceId'],
                            'date': volume['CreateTime'],
                            'desc': desc+":"+attached['Device']+":"+volume['VolumeId'],
                            'old_desc': desc+":"+attached['Device'],
                            'persist': persist,
                            'hourly': args.hourly
                        }
    logger.info("\tTotal Volumes discovered: %s" % (len(my_volumes)))
    logger.info("\tTotal Volumes tagged for deletion: %i" % (len(volume_data)))
    logger.info("\tTotal Volumes tagged for backup: %i" % (len(snapshot_volumes)))
    return True

##
## the following 3 functions are for determining if a volume is in use.
## it results in a longer processing time - disabling for use in lambda
##
# def is_active_volume(args, instance_id):
#     """ Determine if Volume is attached to running instance """
#     if len(args.verbose) >= 3: logger.debug("\tChecking for disk usage on running host: %s" % (instance_id))
#     if instance_id in instance_data and instance_data[instance_id]['state'] == 'running':
#         return True
#     return False

# def is_candidate(args, volume_id, instance_id, region):
#     """ Make sure the volume is candidate for delete """
#     if is_active_volume(args, instance_id):
#         metrics = get_volume_metrics(args, volume_id, region)
#         if len(metrics):
#             for metric in metrics:
#                 if metric['Minimum'] < volume_metric_mininum :
#                     if len(args.verbose) >= 3: logger.debug("\tInactive Volume Tagging Volume for deletion: (%i, %s, %s, %s)" % (metric['Minimum'], instance_data[instance_id]['name'], instance_id, volume_id))
#                     return True
#                 else:
#                     if len(args.verbose) >= 3: logger.debug("\tActive Volume - Ignoring for deletion: (%i, %s, %s, %s)" % (metric['Minimum'], instance_data[instance_id]['name'], instance_id, volume_id))
#                     return False
#         else:
#             if len(args.verbose) >= 3: logger.debug("metrics not returned")
#             return False
#     else:
#         if len(args.verbose) >= 3: logger.debug("%s not active on %s" % (volume_id, instance_id))
#         return True

# def get_volume_metrics(args, volume_id, region):
#     """ Get volume idle time on an individual volume over `start_date` to today """
#     volume_metrics_data = boto3.client('cloudwatch', region_name=region).get_metric_statistics(
#         Namespace='AWS/EBS',
#         MetricName='VolumeIdleTime',
#         Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
#         Period=3600,
#         StartTime=two_weeks,
#         EndTime=today,
#         Statistics=['Minimum'],
#         Unit='Seconds'
#     )
#     if len(args.verbose) >= 3: logger.debug("\t\tReturning datapoints: %s" % (volume_metrics_data['Datapoints']))
#     return volume_metrics_data['Datapoints']

def create_snapshot(args, volume_id, description, old_description, persist):
    """ Create snapshot of volume """
    try:
        if instance_data[all_volumes[volume_id]['instance_id']]['environment']:
            if instance_data[all_volumes[volume_id]['instance_id']]['state'] == "running":
                if not args.dry_run:
                    logger.info("\tCreating Snapshot of %s with Description: %s " % (volume_id, description))
                    if len(args.verbose) >= 3:
                        logger.debug("\tCreating tags:")
                        logger.debug("\t\tName: %s" % (description))
                        logger.debug("\t\tVolume: %s" % (volume_id))
                        logger.debug("\t\tDepartpment: %s" % ("ops"))
                        logger.debug("\t\tInstanceId: %s" % (all_volumes[volume_id]['instance_id']))
                        logger.debug("\t\tEnvironment: %s" % (instance_data[all_volumes[volume_id]['instance_id']]['environment']))
                        logger.debug("\t\tRegion: %s" % (args.region))
                        logger.debug("\t\tApplication: %s" % ("shared"))
                        logger.debug("\t\tRole: %s" % ("ec2"))
                        logger.debug("\t\tService: %s" % ("ebs"))
                        logger.debug("\t\tPersist: %s" % (persist))
                        logger.debug("\t\tCategory: %s" % ("snapshot"))
                    client = boto3.client('ec2', region_name=args.region)
                    create_snap = client.create_snapshot(
                        VolumeId=volume_id,
                        Description=description
                    )
                    if len(args.verbose) >= 3: logger.debug("\t Snapshot created: %s" % (create_snap['SnapshotId']))
                    client.create_tags(
                        Resources=[create_snap['SnapshotId']],
                        Tags = [{
                            'Key': 'Name',
                            'Value': description
                        },{
                            'Key': 'Volume',
                            'Value': volume_id
                        },{
                            'Key': 'Department',
                            'Value': 'Ops'
                        },{
                            'Key': 'Instance',
                            'Value': all_volumes[volume_id]['instance_id']
                        },{
                            'Key': 'Environment',
                            'Value': instance_data[all_volumes[volume_id]['instance_id']]['environment']
                        },{
                            'Key': 'Region',
                            'Value': args.region
                        },{
                            'Key': 'Application',
                            'Value': 'shared'
                        },{
                            'Key': 'Role',
                            'Value': 'ebs'
                        },{
                            'Key': 'Service',
                            'Value': 'ec2'
                        },{
                            'Key': 'Category',
                            'Value': 'snapshot'
                        }]
                    )
                    if len(args.verbose) >= 2: logger.info("\t\t Snapshot %s tags created" % (create_snap['SnapshotId']))
                else:
                    logger.warning("\t(dry-run) Creating Snapshot of %s with Description: %s " % (volume_id, description))
                return 1
    except LookupError as err:
        if len(args.verbose) >= 2: logger.error("\t ** volume_id (%s) not present in dict (%s)" % (volume_id, err))
        pass
    return 0

def delete_snapshot(args, snapshot_id, referrer):
    """ delete_snapshot """
    if not args.dry_run:
        logger.info("\tDeleting snapshot %s (count:%s :: persist:%s)" % (snapshot_id, volume_snapshot_count[snapshot_data[snapshot_id]['volume_id']]['count'], snapshot_data[snapshot_id]['persist']))
        volume_snapshot_count[snapshot_data[snapshot_id]['volume_id']] = { 'count': volume_snapshot_count[snapshot_data[snapshot_id]['volume_id']]['count'] - 1 }
        client = boto3.client('ec2', region_name=args.region)
        client.delete_snapshot(
            # DryRun=True,
            SnapshotId=snapshot_id
        )
    else:
        logger.warning("\t (dry-run) Deleting snapshot %s (count:%s :: persist:%s)" % (snapshot_id, volume_snapshot_count[snapshot_data[snapshot_id]['volume_id']]['count'], snapshot_data[snapshot_id]['persist']))
    return 1

def delete_image(args, ami_id, ami_name):
    """ deregister_image """
    if not args.dry_run:
        logger.warning("\t ( disabled ) - Deregistering Image: %s %s" % (ami_id, ami_name))
    #     client.deregister_image(
    #         # DryRun=True,
    #         ImageId=ami_id
    #     )
    else:
        logger.warning("\t (dry run) ( disabled ) - Deregistering Image: %s %s" % (ami_id, ami_name))
    return True

def handler(event, context):
    parser = argparse.ArgumentParser()
    #parser.add_argument('input', type=str, nargs='+', help='')
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
        default=event['type'],
        help="type"
    )
    parser.add_argument(
        '--region',
        choices=[
            "us-east-1",
            "us-west-1",
            "us-west-2",
            "ap-southeast-1"
        ],
        nargs='?',
        metavar='',
        default=event['region'],
        help="region"
    )
    parser.add_argument(
        '--account_id',
        nargs='?',
        metavar='',
        default=event['account_id'],
        help="account_id"
    )
    parser.add_argument(
        '-v',
        dest='verbose',
        default=event['verbose'],
        nargs='?'
    )
    parser.add_argument(
        '--volume',
        nargs='?',
        default=event['volume'],
        help="VolumeID"
    )
    parser.add_argument(
        '--instance',
        nargs='?',
        default=event['instance'],
        help="InstanceID"
    )
    parser.add_argument(
        '--retention',
        nargs='?',
        default=event['retention'],
        type=int,
        help="Retention"
    )
    parser.add_argument(
        '--rotation',
        nargs='?',
        default=event['rotation'],
        type=int,
        help="Rotation"
    )
    parser.add_argument(
        '--hourly',
        action='store_true',
        default=event['hourly'],
        help="Hourly"
    )
    parser.add_argument(
        '--persist',
        action='store_true',
        default=event['persist'],
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
        default=event['env'],
        help="Environment"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=event['dry_run'],
        help="DryRun"
    )
    args = parser.parse_args()
    logger = logging.getLogger()
    if args.verbose and len(args.verbose)+1 >= 4:
        h.setFormatter(logging.Formatter(_log_debug))
        logger.setLevel(logging.DEBUG)
    elif args.verbose and len(args.verbose)+1 >= 3:
        h.setFormatter(logging.Formatter(_log_critical))
        logger.setLevel(logging.INFO)
    elif args.verbose and len(args.verbose)+1 == 2:
        h.setFormatter(logging.Formatter(_log_error))
        logger.setLevel(logging.WARNING)
    elif args.verbose and len(args.verbose)+1 == 2:
        h.setFormatter(logging.Formatter(_log_error))
        logger.setLevel(logging.ERROR)
    else:
        h.setFormatter(logging.Formatter(_log_info))
        logger.setLevel(logging.INFO)

    # disable boto logging, it's just noise for now
    logging.getLogger('boto').setLevel(logging.CRITICAL)
    logging.getLogger('botocore').setLevel(logging.CRITICAL)
    logger.addHandler(h)

    if args.volume and args.instance:
        logger.error("false. only one option is allowed")
        exit(1)
    if args.volume or args.instance:
        logger.warning("Defaulting to type 'create-snapshot' with inclusiong of arg: %s %s" % (args.instance, args.volume))
        args.type = "create-snapshot"

    logger.info("*** Defined Args ***")
    logger.info("\tverbose: %s" % (args.verbose))
    logger.info("\ttype: %s" % (args.type))
    logger.info("\tenv: %s" % (args.env))
    logger.info("\tvolume: %s" % (args.volume))
    logger.info("\tinstance: %s" % (args.instance))
    logger.info("\tretention: %s" % (args.retention))
    logger.info("\tdry_run: %s" % (args.dry_run))
    logger.info("\tregion: %s" % (args.region))
    logger.info("\taccount_id: %s" % (args.account_id))
    logger.info("\trotation: %s" % (args.rotation))
    logger.info("\thourly: %s" % (args.hourly))
    logger.info("\tpersist: %s" % (args.persist))

    find_instances(args)
    find_volumes(args)
    if args.type != "create-snapshot" or args.type != "create-snapshots":
        find_snapshots(args)
    if not args.volume and not args.instance:
        if args.type != "clean-snapshot" or args.type != "clean-snapshots" or args.type != "clean-volume" or args.type != "clean-volumes":
            find_images(args)
    if args.type == "all" or args.type == "clean-snapshot" or args.type == "clean-snapshots" or args.type == "clean":
        snapshot_count = 0
        logger.warning('Ignoring any env flag for cleanup: %s' % (args.env))
        logger.info("*** Cleaning Snapshots ***")
        for snapshot in snapshot_data:
            if volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'] > args.rotation and not snapshot_data[snapshot]['persist'] and not snapshot_data[snapshot]['id'] in image_data:
                if len(args.verbose) >= 3:
                    logger.debug("******")
                    logger.debug("\tsnapshot id: %s" % (snapshot_data[snapshot]['id']))
                    logger.debug("\tsnap_vol: %s" % (snapshot_data[snapshot]['volume_id']))
                    logger.debug("\tsnap_desc: %s" % (snapshot_data[snapshot]['description']))
                    logger.debug("\tsnap_date: %s" % (snapshot_data[snapshot]['date']))
                    logger.debug("\tsnap_ratio: %s" % (snapshot_data[snapshot]['ratio']))
                    logger.debug("\tsnap_age: %s" % (snapshot_data[snapshot]['age']))
                    logger.debug("\tsnap_persist: %s" % (snapshot_data[snapshot]['persist']))
                    logger.debug("\tsnap_method: %s" % (snapshot_data[snapshot]['method']))
                    logger.debug("\tsnap_count: %s" % (snapshot_data[snapshot]['snap_count']))
                    logger.debug("\tvolume_snapshot_count: %s" % (volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count']))
                    logger.debug("\trotation_scheme: %i" % (args.rotation))
                    logger.debug("\tDeleting %s - [ snap_count:%s, volume_count:%s, persist: %s ]" % (snapshot_data[snapshot]['id'], snapshot_data[snapshot]['snap_count'], volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'], snapshot_data[snapshot]['persist']))
                if snapshot_data[snapshot]['volume_id'] not in all_volumes:
                    if len(args.verbose) >= 3: logger.debug("\tvol: %s snap: %s snap_count: %s rotate: %i" % (snapshot_data[snapshot]['volume_id'], snapshot_data[snapshot]['id'], volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'], args.rotation))
                    ret_val = delete_snapshot(args, snapshot_data[snapshot]['id'], '')
                    snapshot_count = snapshot_count + ret_val
                    volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'] = volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'] - ret_val
                else:
                    if len(args.verbose) >= 3: logger.debug("\tvol: %s snap: %s snap_count: %s rotate: %i" % (snapshot_data[snapshot]['volume_id'], snapshot_data[snapshot]['id'], volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'], args.rotation))
                    ret_val = delete_snapshot(args, snapshot_data[snapshot]['id'], 'delete_snapshot')
                    snapshot_count = snapshot_count + ret_val
                    volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'] = volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'] - ret_val
            else:
                if len(args.verbose) >= 3: logger.debug("\tIgnoring deletion of %s - [ snap_count:%s, volume_count:%s, persist: %s ]" % (snapshot_data[snapshot]['id'], snapshot_data[snapshot]['snap_count'], volume_snapshot_count[snapshot_data[snapshot]['volume_id']]['count'], snapshot_data[snapshot]['persist']))
        logger.info("\t ** Total Snapshots Deleted: %s" % (snapshot_count))

    ##
    ## disabling operations that determine if a volume is in active or not.
    ## like above, not necessary right now for when lambda runs the code
    ##
    # if args.type == "all" or args.type == "clean-volume" or args.type == "clean-volumes" or args.type == "clean":
    #     volume_count = 0
    #     if len(args.verbose) >= 3: logger.debug("Ignoring any env flag for cleanup: %s" % (args.env))
    #     logger.info("*** Cleaning Volumes ***")
    #     logger.warning("\t ** Note: this tags items with tag { 'Delete': 'True' }")
    #     for volume in volume_data:
    #         volume_count = volume_count + 1
    #         if len(args.verbose) >= 3: logger.debug("******")
    #         if len(args.verbose) >= 3: logger.debug("\tvolume_id: %s" % (volume_data[volume]['id']))
    #         if len(args.verbose) >= 3: logger.debug("\tvolume_instance_id: %s" % (volume_data[volume]['instance_id']))
    #         if len(args.verbose) >= 3: logger.debug("\tvolume_date: %s" % (volume_data[volume]['date']))
    #     logger.info("\t ** Total Volumes To Delete: %s" % (volume_count))

    if args.type == "all" or args.type == "clean-ami" or args.type == "clean" or args.type == "clean-images" :
        image_count = 0
        if len(args.verbose) >= 3: logger.debug("Ignoring any env flag for cleanup: %s" % (args.env))
        logger.info("*** Cleaning Images ***")
        for image in image_data:
            image_count = image_count + 1
            if len(args.verbose) >= 3: logger.debug("******")
            if len(args.verbose) >= 3: logger.debug("\tami_id: %s" % (image_data[image]['id']))
            if len(args.verbose) >= 3: logger.debug("\tami_name: %s" % (image_data[image]['name']))
            if len(args.verbose) >= 3: logger.debug("\tami_attachment_id: %s" % (image_data[image]['date']))
            if len(args.verbose) >= 3: logger.debug("\tami_snapshot_id: %s" % (image_data[image]['snapshot_id']))
            if len(args.verbose) >= 3: logger.debug("\tami_persist: %s" % (image_data[image]['persist']))
            if len(args.verbose) >= 3: logger.debug("\tami_build_method: %s" % (image_data[image]['build_method']))
            # this is disabled for now until we're sure we want to auto delete AMI's
            # if not image_data[image]['persist']:
            #     for ami_snapshot in image_data[image]['snapshot_id']:
            #         delete_snapshot(ami_snapshot, 'delete_image')
            #     delete_image(image_data[image]['id'], image_data[image]['name'])
        logger.info("\t ** Total Images Deregistered: %s" % (image_count))

    if args.type == "all" or args.type == "create-snapshot" or args.type == "create-snapshots":
        snapshot_count = 0
        logger.info("*** Creating Snapshots ***")
        for s_volume in snapshot_volumes:
            if len(args.verbose) >= 3: logger.debug("******")
            if len(args.verbose) >= 3: logger.debug("\tsnapshot_volume['volume_id']: %s" % (snapshot_volumes[s_volume]['id']))
            if len(args.verbose) >= 3: logger.debug("\tsnapshot_volume['instance_id']: %s" % (snapshot_volumes[s_volume]['instance_id']))
            if len(args.verbose) >= 3: logger.debug("\tsnapshot_volume['date']: %s" % (snapshot_volumes[s_volume]['date']))
            if len(args.verbose) >= 3: logger.debug("\tsnapshot_volume['desc']: %s" % (snapshot_volumes[s_volume]['desc']))
            if len(args.verbose) >= 3: logger.debug("\tsnapshot_volume['old_desc']: %s" % (snapshot_volumes[s_volume]['old_desc']))
            if len(args.verbose) >= 3: logger.debug("\tsnapshot_volume['persist']: %s" % (snapshot_volumes[s_volume]['persist']))
            if len(args.verbose) >= 3: logger.debug("\tsnapshot_volume['hourly']: %s" % (snapshot_volumes[s_volume]['hourly']))
            snapshot_count = snapshot_count +create_snapshot(args, snapshot_volumes[s_volume]['id'], snapshot_volumes[s_volume]['desc'], snapshot_volumes[s_volume]['old_desc'], snapshot_volumes[s_volume]['persist'])
        logger.info("\t ** Total Volumes to Snapshot: %s" % (snapshot_count))
    logger.info("*** Operations Complete ***")
    return True
