#!/usr/bin/env python
""" docstring """
import time
import sys
import boto3
region = "us-east-1"
account_id = "12345618999"
ec2_data = {}
s_groups = []
disks = []
source_instance_id = "i-123456"
source_image = "ami-123454"
epoch = int(time.time())
environment = "staging"
ami_base = "mongodb-"+environment
ami_filter = ami_base+"*"
ami_name = ami_base+"_"+str(epoch)
ec2_filter = ami_base+"*"
ec2_name = ami_base+"_"+str(epoch)
delete_snapshots = []
delete_images = []
delete_instances = []
deregister_wait = 240
create_wait = 240
user_data = """#!/bin/sh
/bin/sed -i -e 's/replSet = scorecard//g' /etc/mongod.conf && service mongod restart"""

def snapshot_wait(wait_string, description, volume):
    """ docstring """
    print "\t\tWaiting on %s of %s for snapshot %s to complete..." % (wait_string, volume, description)
    waiter = ec2_client.get_waiter(wait_string)
    waiter.wait(
        Filters=[{
            'Name': 'description',
            'Values': [description]
        }],
    )
    return 0

def ec2_wait(wait_string, instance_id):
    """ docstring """
    print "\tWaiting on %s of %s to complete..." % (wait_string, instance_id)
    waiter = ec2_client.get_waiter(wait_string)
    waiter.wait(
        InstanceIds=[instance_id],
    )
    return 0

def delete_image(image_from_list):
    """ docstring """
    print "\t\tDeregistering Image %s" % (image_from_list)
    ec2_client.deregister_image(ImageId=image_from_list)
    return 0

def delete_snapshot(snapshot_from_list):
    """ docstring """
    print "\t\tDeleting snapshot %s" % (snapshot_from_list)
    ec2_client.delete_snapshot(
        SnapshotId=snapshot_from_list
    )
    return 0

def create_snapshot(volume, description):
    """ docstring """
    print "\t\tCreating snapshot %s of %s" % (description, volume)
    ec2_client.create_snapshot(
        VolumeId=volume,
        Description=description,
    )
    snapshot_wait("snapshot_completed", description, volume)
    return 0

def get_image(image_name):
    """ docstring """
    return_images = []
    print "\tget_image(%s)" % (image_name)
    try:
        images = ec2_client.describe_images(
            Filters=[{
                'Name': 'name',
                'Values': [image_name]
            }]
        )
    except Exception:
        images = {}
    if len(images['Images']) > 0:
        print "\timages_len: %i" % (len(images['Images']))
        for index, this in enumerate(images['Images'], start=0):
            return_images.append(this['ImageId'])
        print "\tReturning image_id: %s" % (return_images)
        return return_images
    else:
        print "\t *** No Images were found"
        return 1


def get_snapshot(volume, description):
    """ docstring """
    return_snapshots = []
    print "\tSearching for snapshot of disk %s %s" % (volume, description)
    try:
        snapshots = ec2_client.describe_snapshots(
            Filters=[{
                'Name': 'owner-id',
                'Values': [account_id]
            }, {
                'Name': 'volume-id',
                'Values': [volume]
            }, {
                'Name': 'description',
                'Values': [description]
            }]
        )
    except Exception:
        snapshots = {}
    if len(snapshots['Snapshots']) > 0:
        print "\t\tsnapshot_len: %i" % (len(snapshots['Snapshots']))
        for index, this in enumerate(snapshots['Snapshots'], start=0):
            return_snapshots.append(this['SnapshotId'])
        print "\t\tReturning snapshot_id: %s" % (return_snapshots)
        return return_snapshots
    else:
        print "\t\t *** No snapshots were found"
        return 1


def getNodes():
    """ docstring """
    instances = ec2_client.describe_instances(
        Filters=[{
            'Name': 'instance-id',
            'Values': [source_instance_id]
        }]
    )
    for instance in instances['Reservations'][0]['Instances']:
        for index, this in enumerate(instance['SecurityGroups'], start=0):
            s_groups.append(this['GroupId'])
        for index, this in enumerate(instance['BlockDeviceMappings'], start=0):
            snapshot_base = ""
            short = this['DeviceName'].split("/")[2]
            try:
                ephemeral = False
                snapshot_base = "mongodb-staging_%s_%s" % (this['Ebs']['VolumeId'], short)
                snapshot_filter = snapshot_base+"*"
                snapshot_desc = snapshot_base+"_"+str(epoch)
                print "\nDevice %i: %s %s %s %s" % (index, this['Ebs']['VolumeId'], short, snapshot_filter, snapshot_desc)
                del_snap = get_snapshot(this['Ebs']['VolumeId'], snapshot_filter)
                if del_snap != 1 and del_snap != 2 and len(del_snap) > 0:
                    for snapshot_item in del_snap:
                        print "\t\t *** Adding %s to delete_snapshots" % (snapshot_item)
                        delete_snapshots.append(snapshot_item)
                else:
                    print "\t\tSnapshot(1) not found (%s, %s)" % (this['Ebs']['VolumeId'], snapshot_filter)
                    print "\t\tThis is not a big deal - old snapshot simply isn't there"
                create_snapshot(this['Ebs']['VolumeId'], snapshot_desc)
                snapshot_id = get_snapshot(this['Ebs']['VolumeId'], snapshot_desc)[0]
                if snapshot_id != 1 and snapshot_id != 2 and len(snapshot_id) > 0:
                    info = {
                        "DeviceName": this['DeviceName'],
                        "Ebs": {
                            "SnapshotId": snapshot_id,
                            "DeleteOnTermination": True,
                            "VolumeType": "gp2"
                        }
                    }
                    disks.append(info)
                    print "\t\tDisk Shortname: %s" % (short)
                    print "\t\tSnapshot Id: %s" % (snapshot_id)
                    print "\t\tDisk Len: %i" % (len(disks))
                else:
                    print "\t\tSnapshot(2) not found( %s, %s)" % (this['Ebs']['VolumeId'], snapshot_desc)
                    exit(3)
            except Exception:
                ephemeral = True
        if len(disks) > 0:
            ec2_data['ec2'] = {
                'RootDeviceType': instance['RootDeviceType'],
                'KeyName': 'base',
                'InstanceType': instance['InstanceType'],
                'VpcId': instance['VpcId'],
                'SubnetId': instance['SubnetId'],
                'RootDeviceName': instance['RootDeviceName'],
                'SecurityGroups': s_groups,
                'Disks': disks,
                'KernelId': instance['KernelId'],
                'VirtualizationType': instance['VirtualizationType'],
                'AvailabilityZone': instance['Placement']['AvailabilityZone'],
                'Tenancy': instance['Placement']['Tenancy'],
                'EbsOptimized': instance['EbsOptimized']
            }
            ec2_data['iam'] = {
                'IamInstanceProfile_id': instance['IamInstanceProfile']['Id'],
                'IamInstanceProfile_arn': instance['IamInstanceProfile']['Arn']
            }
            print "SecurityGroups: %s" % (ec2_data['ec2']['SecurityGroups'])
        else:
            print "Disks are empty"
            exit(2)
    return ec2_data

def create_image(instance_data):
    """ docstring """
    print "Creating Image"
    print "\tReceived Values:\n %s\n" % (instance_data)
    found_image_id = get_image(ami_filter)
    print "\tFound Image(s): %s" % (found_image_id)
    if found_image_id != 1 and found_image_id != 2 and len(found_image_id) > 0:
        for item_a in found_image_id:
            print "\t *** Adding %s to delete_images" % (item_a)
            delete_images.append(item_a)
    ec2_client.register_image(
        DryRun=False,
        Name=ami_name,
        Description=ami_name,
        Architecture="x86_64",
        RootDeviceName=instance_data['ec2']['RootDeviceName'],
        BlockDeviceMappings=instance_data['ec2']['Disks']
    )
    print "\tSleeping for %i to allow the image to start creating" % (create_wait)
    time.sleep(create_wait)
    if found_image_id != 1 and found_image_id != 2 and len(found_image_id) > 0:
        found_image_id = get_image(ami_name)[0]
        print "\tFound image: %s" % (found_image_id)
        ec2_data['ami'] = {
            'image_id': found_image_id
        }
        waiter = ec2_client.get_waiter('image_exists')
        waiter.wait(
            DryRun=False,
            ImageIds=[found_image_id]
        )
        ec2_client.create_tags(
            Resources=[found_image_id],
            Tags=[{
                'Key': 'Name',
                'Value': ami_name
            }, {
                'Key': 'Description',
                'Value': ami_name
            }]
        )
        return 0
    else:
        print "Created Image not found"
        return 5
def create_instance(options):
    """ docstring """
    print "Create Instance"
    print "\t Received Options:\n %s" % (options)
    print """
    ec2_client.create_instances(
        DryRun=True,
        ImageId=%s,
        MinCount=1,
        MaxCount=1,
        KeyName=%s,
        SecurityGroupIds=%s,
        UserData=%s,
        InstanceType=%s,
        BlockDeviceMappings=%s,
        Monitoring={ 'Enabled': True },
        SubnetId=%s,
        DisableApiTermination=False,
        InstanceInitiatedShutdownBehavior='stop',
        IamInstanceProfile={ 'Arn': %s },
        KernelId=%s,
        Placement={
            'AvailabilityZone': %s,
            'GroupName': '',
            'Tenancy': '%s'
        },
    )
    """ % (options['ami']['image_id'], options['ec2']['KeyName'], options['ec2']['SecurityGroups'], user_data, options['ec2']['InstanceType'], options['ec2']['Disks'], options['ec2']['SubnetId'], options['iam']['IamInstanceProfile_arn'], options['ec2']['KernelId'], options['ec2']['AvailabilityZone'], options['ec2']['Tenancy'])
    create_host = ec2_client.run_instances(
        DryRun=False,
        ImageId=options['ami']['image_id'],
        MinCount=1,
        MaxCount=1,
        KeyName=options['ec2']['KeyName'],
        SecurityGroupIds=options['ec2']['SecurityGroups'],
        UserData=user_data,
        InstanceType=options['ec2']['InstanceType'],
        BlockDeviceMappings=options['ec2']['Disks'],
        Monitoring={'Enabled': True},
        SubnetId=options['ec2']['SubnetId'],
        DisableApiTermination=False,
        InstanceInitiatedShutdownBehavior='stop',
        IamInstanceProfile={'Arn': options['iam']['IamInstanceProfile_arn']},
        KernelId=options['ec2']['KernelId'],
        Placement={
            'AvailabilityZone': options['ec2']['AvailabilityZone'],
            'GroupName': '',
            'Tenancy': options['ec2']['Tenancy']
        },
    )
    print "\tcreate_hosts returns: \n %s" % (create_host)
    print "\tReturning Instance ID: %s" % (create_host['Instances'][0]['InstanceId'])
    ec2_wait("instance_status_ok", create_host['Instances'][0]['InstanceId'])
    ec2_client.create_tags(
        Resources=[create_host['Instances'][0]['InstanceId']],
        Tags=[{
            'Key': 'Name',
            'Value': ec2_name
        }, {
            'Key': 'Environment',
            'Value': environment
        }, {
            'Key': 'Region',
            'Value': region
        }]
    )
    found_instances = get_instances(create_host['Instances'][0]['InstanceId'])
    if len(found_instances) > 0:
        print "\tFound_Instances: %s" % (found_instances)
    else:
        print "No old instances are running"
    return 0

def get_instances(instance_id):
    """ docstring """
    print "\tget_instances(%s)" % (instance_id)
    try:
        instances = ec2_client.describe_instances(
            Filters=[{
                "Name" : "tag-key",
                "Values" : ["Name"]
            }, {
                "Name" : "tag-value",
                "Values" : [ec2_filter]
            }, {
                'Name':'instance-state-name',
                'Values': ['running']
            }]
        )
    except Exception:
        instances = {}
    if len(instances['Reservations']) > 0:
        print "\tinstances_len: %i" % (len(instances['Reservations']))
        for index, this in enumerate(instances['Reservations'], start=0):
            if this['Instances'][0]['InstanceId'] != instance_id:
                delete_instances.append(this['Instances'][0]['InstanceId'])
        print "\tReturning return_instances: %s" % (delete_instances)
        return delete_instances
    else:
        print "\t *** No Instances were found"
        return 1

def terminate_instances(instance_id):
    """ docstring """
    print "\tterminate_instance recevied: %s" % (instance_id)
    ec2_client.terminate_instances(
        DryRun=False,
        InstanceIds=[instance_id,]
    )
    print "\tWaiting for instance %s to terminate" % (instance_id)
    ec2_wait("instance_terminated", instance_id)
    return 0

class Unbuffered(object):
    """ Class to push stdout buffer to screen immediately """
    def __init__(self, stream):
        """ docstring for linter """
        self.stream = stream
    def write(self, self_data):
        """ docstring for linter """
        self.stream.write(self_data)
        self.stream.flush()
    def __getattr__(self, attr):
        """ docstring for linter """
        return getattr(self.stream, attr)

if __name__ == "__main__":
    sys.stdout = Unbuffered(sys.stdout)
    ec2_client = boto3.client('ec2', region_name=region)
    host_data = getNodes()
    create_image(host_data)
    if len(delete_images) > 0:
        print "Delete Images:"
        for item in delete_images:
            print "\t - %s" % (item)
            delete_image(item)
    if len(delete_snapshots) > 0:
        print "Delete snapshots:"
        for item in delete_snapshots:
            print "\t - %s" % (item)
            delete_snapshot(item)
    create_instance(ec2_data)
    if len(delete_instances) > 0:
        print "Terminate Instances: %s" % (delete_instances)
        for item in delete_instances:
            print "\t - %s" % (item)
            terminate_instances(item)
    print "TODO: Update DNS of host/service with new host ip"
    print "Completing Operation."
    exit(0)
