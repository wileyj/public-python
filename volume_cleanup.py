#!/usr/bin/env python
""" script to do something """
import time
from difflib import SequenceMatcher
from datetime import datetime, timedelta
import argparse
import logging
import boto3
from boto3.session import Session

region = "us-east-1"
account_id = "1234567890"
session = Session()
ec2 = session.resource('ec2', region_name=region)
client = boto3.client('ec2', region_name=region)
cloudwatch = boto3.client("cloudwatch", region_name=region)
image_data = {}
used_images = {}
used_snapshots = {}
used_volumes = {}
snapshot_volumes = {}
used_instances = {}
current_time = int(round(time.time()))
retention = 3 # if volume is destroyed, keep the snapshot around for x days
full_day = 86400
today = datetime.now() + timedelta(days=1)
two_weeks_ago = timedelta(days=retention)
start_date = today - two_weeks_ago

instance_whitelist = {
    'i-123456',
    'i-234567'
}

def find_instances():
    """ Function to retrieve all instance details """
    print "Retrieving Non-Classic Instances"
    my_instances = client.describe_instances()
    print "Retrieving Classic Instances"
    list_classic_instances = client.describe_classic_link_instances()
    for x in my_instances['Reservations']:
        i_name = x['Instances'][0]['InstanceId']
        try:
            for tag in x['Instances'][0]['Tags']:
                if tag['Key'] == "Name":
                    i_name = tag['Value']
                    # used_instances[x['Instances'][0]['InstanceId']].update({'name': tag['Value']})
        except Exception:
            i_name = x['Instances'][0]['InstanceId']
        if (x['Instances'][0]['State']['Name'] == "running" or x['Instances'][0]['InstanceId'] in instance_whitelist) and 'VpcId' in x['Instances'][0]:
            used_instances[x['Instances'][0]['InstanceId']] = {
                'id': x['Instances'][0]['InstanceId'],
                'state': x['Instances'][0]['State']['Name'],
                'type': x['Instances'][0]['InstanceType'],
                'private_dns': x['Instances'][0]['PrivateDnsName'],
                'launch_time': x['Instances'][0]['LaunchTime'],
                'name': i_name
            }
    for c_instance in list_classic_instances['Instances']:
        my_instances = client.describe_instances(
            Filters=[{
                'Name': 'instance-id',
                'Values': [c_instance['InstanceId']]
            }]
        )
        for x in my_instances['Reservations']:
            i_name = x['Instances'][0]['InstanceId']
        if x['Instances'][0]['State']['Name'] == "running" or x['Instances'][0]['InstanceId'] in instance_whitelist or 'VpcId' not in x['Instances'][0]:
            for tag in x['Instances'][0]['Tags']:
                if tag['Key'] == "Name":
                    i_name = tag['Value']
        used_instances[x['Instances'][0]['InstanceId']] = {
            'id': x['Instances'][0]['InstanceId'],
            'state': x['Instances'][0]['State']['Name'],
            'type': x['Instances'][0]['InstanceType'],
            'private_dns': x['Instances'][0]['PrivateDnsName'],
            'launch_time': x['Instances'][0]['LaunchTime'],
            'name': i_name
        }
    return used_instances

def find_images():
    """ Function to retrieve ami details """
    print "Retrieving images"
    my_images = client.describe_images(Owners=[account_id])
    my_instances = client.describe_instances()
    for x in my_images['Images']:
        set_buildmethod = "False"
        set_persist = "False"
        try:
            for t in x['Tags']:
                if t['Key'] == "Persist":
                    set_persist = t['Value']
                if t['Key'] == "BuildMethod":
                    set_buildmethod = t['Value']
        except Exception:
            set_persist = "False"
            set_buildmethod = "False"
        if set_persist == "True":
            print "\tFound Persist Tag (%s) in image (%s)" % (set_persist, x['ImageId'])
        else:
            snapshot_data = []
            for index, this in enumerate(x['BlockDeviceMappings'], start=0):
                # if not this['DeviceName']['VirtualName']:
                try:
                    snapshot_data.append(this['Ebs']['SnapshotId'])
                    ephemeral = False
                except Exception:
                    ephemeral = True
            image_data[x['ImageId']] = {
                'id': x['ImageId'],
                'name': x['Name'],
                'date': x['CreationDate'],
                'persist': set_persist,
                'build_method': set_buildmethod,
                'snapshot_id': snapshot_data
            }
    for ami in my_instances['Reservations']:
        remove_from_dict = 1
        if ami['Instances'][0]['InstanceId'] in instance_whitelist:
            print "\tFound image (%s) in whitelist" % (ami['Instances'][0]['ImageId'])
            remove_from_dict = 1
        elif ami['Instances'][0]['InstanceId'] in instance_dict:
            print "\tFound image (%s) used by instance (%s)" % (ami['Instances'][0]['ImageId'], ami['Instances'][0]['InstanceId'])
            remove_from_dict = 1
        else:
            print "\tFlagging image (%s) for deletion" % (ami['Instances'][0]['ImageId'])
            remove_from_dict = 0
        if remove_from_dict != 0:
            try:
                if image_data[ami['Instances'][0]['ImageId']]['persist'] != "True" or image_data[ami['Instances'][0]['ImageId']]['build_method'] != "Packer":
                    print "\tRemoving %s (%s) from image_data dict (persist: %s)" % (image_data[ami['Instances'][0]['ImageId']]['name'], image_data[ami['Instances'][0]['ImageId']]['id'], image_data[ami['Instances'][0]['ImageId']]['persist'])
                    del image_data[ami['Instances'][0]['ImageId']]
            except Exception:
                print "\tAMI %s used by %s (persist is true or build_method is packer) not listed in image_dict" % (ami['Instances'][0]['ImageId'], ami['Instances'][0]['InstanceId'])
    return image_data

def find_snapshots():
    """ Function to retrieve snapshot details """
    print "Retrieving Snapshots"
    my_snapshots = client.describe_snapshots(
        Filters=[{
            'Name': 'owner-id',
            'Values': [account_id]
        }]
    )
    for x in my_snapshots['Snapshots']:
        epoch = int(x['StartTime'].strftime("%s"))
        diff = current_time - epoch
        age = diff/full_day
        try:
            for t in x['Tags']:
                if t['Key'] == "BuildMethod":
                    method = t['Value']
        except Exception:
            method = "non-packer"
        match_ratio = SequenceMatcher(
            lambda x:
            x == " ",
            "Created by CreateImage(i-",
            x['Description']
        ).ratio()
        if match_ratio < 0.53 or match_ratio > 0.54:
            # not a snapshot created by an ami
            if age > retention and method != "Packer":
                used_snapshots[x['SnapshotId']] = {
                    'id': x['SnapshotId'],
                    'volume_id': x['VolumeId'],
                    'description': x['Description'],
                    'date': x['StartTime'],
                    'ratio': match_ratio,
                    'age': age,
                    'method': method
                }
    return used_snapshots

def find_volumes():
    """ function to do something """
    print "Retrieving Volume Data"
    my_volumes = client.describe_volumes()
    for x in my_volumes['Volumes']:
        for y in x['Attachments']:
            i_id = y['InstanceId']
            i_attachment = y['VolumeId']
            if is_candidate(x['VolumeId'], i_id):
                if i_id not in instance_whitelist and i_id not in instance_dict:
                    used_volumes[x['VolumeId']] = {
                        'id': x['VolumeId'],
                        'attachment_id': i_attachment,
                        'instance_id': i_id,
                        'snapshot_id': x['SnapshotId'],
                        'date': x['CreateTime']
                    }
    return used_volumes

def find_snapshot_volumes():
    """ Function to find volumes to snapshot """
    print "Retrieving Volume Data to Snapshot"
    my_snap_volumes = client.describe_volumes()
    for x in my_snap_volumes['Volumes']:
        if x['VolumeId'] not in volume_dict and len(x['Attachments']) > 0:
            for y in x['Attachments']:
                s_desc = "NULL"
                if y['InstanceId'] not in instance_dict:
                    s_desc = y['InstanceId']
                else:
                    s_desc = instance_dict[y['InstanceId']]['name'].replace(" - ", "-")
                s_desc = s_desc.replace(")", "")
                s_desc = s_desc.replace("(", "")
                s_desc = s_desc.replace(" ", "-")
                s_desc = s_desc+"_"+x['VolumeId']
                snapshot_volumes[x['VolumeId']] = {
                    'id': x['VolumeId'],
                    'instance_id': y['InstanceId'],
                    'date': x['CreateTime'],
                    'desc': s_desc
                }
    return snapshot_volumes

def is_active_volume(instance_id):
    """ Determine if Volume is being used or not """
    # print "\tChecking for disk usage on host: %s" % (instance_id))
    if instance_id in instance_dict:
        return True
    elif instance_id in instance_whitelist:
        return True
    else:
        return False

def is_candidate(volume_id, instance_id):
    """ Make sure the volume is candidate for delete """
    if not is_active_volume(instance_id):
        metrics = get_metrics(volume_id)
        if len(metrics) != 0:
            for metric in metrics:
                if metric['Minimum'] < 299:
                    return False
        return True
    else:
        return False

def get_metrics(volume_id):
    """Get volume idle time on an individual volume over `start_date` to today"""
    metrics = cloudwatch.get_metric_statistics(
        Namespace='AWS/EBS',
        MetricName='VolumeIdleTime',
        Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
        Period=3600,
        StartTime=start_date,
        EndTime=today,
        Statistics=['Minimum'],
        Unit='Seconds'
    )
    return metrics['Datapoints']

class VAction(argparse.Action):
    """ docstring """
    def __call__(self, argparser, cmdargs, values, option_string=None):
        if values is None:
            values = '1'
        try:
            values = int(values)
        except ValueError:
            values = values.count('v') + 1
        setattr(cmdargs, self.dest, values)

def create_snapshot(volume_id, description):
    """ Create snapshot of volume """
    snapshot_data = client.describe_snapshots(
        Filters=[{
            'Name': 'owner-id',
            'Values': [account_id]
        }, {
            'Name': 'description',
            'Values': [description]
        }]
    )
    if len(snapshot_data) != 0:
        for found_snapshot in snapshot_data['Snapshots']:
            print "Found snapshot: %s" % (found_snapshot['SnapshotId'])
            delete_snapshot(found_snapshot['SnapshotId'])
    print "Create Snapshot of %s with Description: %s " % (volume_id, description)
    client.create_snapshot(
        VolumeId=volume_id,
        Description=description
    )
    return 0

def delete_snapshot(snapshot_id):
    """ delete snapshot """
    print "Deleting existing snapshot %s" % (snapshot_id)
    client.delete_snapshot(
        SnapshotId=snapshot_id
    )
    return 0

def delete_image(ami_id):
    """deregister image"""
    print "Deregistering Image: %s" % (ami_id)
    client.deregister_image(
        ImageId=ami_id
    )
    return image_count

def delete_volume(volume_id):
    """ delete volume"""
    print "[ Disabled delete_volume function ] - %s" % (volume_id)
#     data = client.describe_volumes(
#         Filters=[{
#             'Name': 'volume-id',
#             'Values': [volume_id]
#         }]
#     )
#     for volume in data['Volumes']:
#         for item in volume['Attachments']:
#             if volume['State'] != "available":
#                 volumes = ec2.instances.filter(
#                     Filters=[{
#                         'Name': 'instance-id',
#                         'Values': [item['InstanceId']]
#                     }]
#                 )
#                 for instance in volumes:
#                     if instance.state['Name'] == "stopped" and dryrun == False:
#                         print "[ SKIPPING ] Deleting Volume %s" % (volume['VolumeId'])
#                         volume_count = volume_count + 1
#                         # client.delete_volume(
#                         #     VolumeId=volume['VolumeId']
#                         # )
#                         #print "Volume data.delete(DryRun=True)"
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--type',
        nargs='?',
        metavar='',
        default="ami",
        help="type: clean-ami, clean-snapshot, clean-volume, create-snapshot, all"
    )
    parser.add_argument(
        '-v',
        nargs='?',
        action=VAction,
        dest='verbose'
    )
    args = parser.parse_args()
    if args.verbose:
        if args.verbose == 4:
            logging.basicConfig(level=logging.DEBUG)
        elif args.verbose == 3:
            logging.basicConfig(level=logging.ERROR)
        elif args.verbose == 2:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)
    instance_dict = find_instances()
    image_dict = find_images()
    snapshot_dict = find_snapshots()
    volume_dict = find_volumes()
    snapshot_volume_dict = find_snapshot_volumes()
    snap_count = 0
    ami_count = 0
    volume_count = 0
    instance_count = 0
    image_count = 0
    create_snap = 0

    # for instance in instance_dict:
    #     instance_count = instance_count + 1
    #     print "")
    #     print "\tec2_id: %s" % (instance_dict[instance]['id']))
    #     print "\tec2_state: %s" % (instance_dict[instance]['state']))
    #     print "\tec2_type: %s" % (instance_dict[instance]['type']))
    #     print "\tec2_private_dns: %s" % (instance_dict[instance]['private_dns']))
    #     print "\tec2_launch_time: %s" % (instance_dict[instance]['launch_time']))
    #     print "\tec2_name: %s" % (instance_dict[instance]['name']))
    # print "\tTotal Instances Running: %s" % (instance_count)

    if args.type == "all" or args.type == "clean-snapshot":
        for snapshot in snapshot_dict:
            snap_count = snap_count + 1
            print ""
            print "snap_id: %s" % (snapshot_dict[snapshot]['id'])
            print "\tsnap_vol: %s" % (snapshot_dict[snapshot]['volume_id'])
            print "\tsnap_desc: %s" % (snapshot_dict[snapshot]['description'])
            print "\tsnap_date: %s" % (snapshot_dict[snapshot]['date'])
            print "\tsnap_ratio: %s" % (snapshot_dict[snapshot]['ratio'])
            print "\tsnap_age: %s" % (snapshot_dict[snapshot]['age'])
            print "\tsnap_method: %s" % (snapshot_dict[snapshot]['method'])
            delete_snapshot(snapshot_dict[snapshot]['id'])
        print "\tTotal Snapshots: %s" % (snap_count)

    if args.type == "all" or args.type == "clean-ami":
        for image in image_dict:
            image_count = image_count + 1
            print ""
            print "ami_id: %s" % (image_dict[image]['id'])
            print "\tami_name: %s" % (image_dict[image]['name'])
            print "\tami_attachment_id: %s" % (image_dict[image]['date'])
            print "\tami_snapshot_id: %s" % (image_dict[image]['snapshot_id'])
            print "\tami_persist: %s" % (image_dict[image]['persist'])
            print "\tami_build_method: %s" % (image_dict[image]['build_method'])
            for snap in image_dict[image]['snapshot_id']:
                print "\t\tami_snapshot_id: %s" % (snap)
            if image_dict[image]['persist'] != "True":
                delete_image(image_dict[image]['id'])
        print "\tTotal Images: %s" % (image_count)

    if args.type == "all" or args.type == "clean-volume":
        for volume in volume_dict:
            volume_count = volume_count + 1
            print "volume_id: %s" % (volume_dict[volume]['id'])
            print "\tvolume_instance_id: %s" % (volume_dict[volume]['instance_id'])
            print "\tvolume_date: %s" % (volume_dict[volume]['date'])
            print ""
        print "\tTotal Volumes: %s" % (volume_count)

    if args.type == "all" or args.type == "create-snapshot":
        for s_volume in snapshot_volume_dict:
            create_snap = create_snap + 1
            print ""
            print "create_id: %s" % (snapshot_volume_dict[s_volume]['id'])
            print "\tcreate_instance: %s" % (snapshot_volume_dict[s_volume]['instance_id'])
            print "\tcreate_date: %s" % (snapshot_volume_dict[s_volume]['date'])
            print "\tcreate_desc: %s" % (snapshot_volume_dict[s_volume]['desc'])
            create_snapshot(snapshot_volume_dict[s_volume]['id'], snapshot_volume_dict[s_volume]['desc'])
        print "\tTotal Volumes to Snapshot: %s" % (create_snap)
