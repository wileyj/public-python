import time
from difflib import SequenceMatcher
from datetime import datetime, timedelta
import argparse
import logging
import boto3

region = "us-east-1"
account_id = "1234567899"
print "Retrieving images"
image_data = {}
set_persist = "False"
set_buildmethod = "False"
client = boto3.client('ec2', region_name=region)
my_images = client.describe_images(Owners=[account_id])
for x in my_images['Images']:
    set_buildmethod = "False"
    set_persist = "False"
    print "x: %s" % (x)
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
        # print "image: %s" % (x)
        # print "disk len: %i" % (len(x['BlockDeviceMappings']))
        for index, this in enumerate(x['BlockDeviceMappings'], start=0):
            # if not this['DeviceName']['VirtualName']:
            try:
                snapshot_data.append(this['Ebs']['SnapshotId'])
                ephemeral = False
            except Exception:
                ephemeral = True
            # except Exception:
        image_data[x['ImageId']] = {
            'id': x['ImageId'],
            'name': x['Name'],
            'date': x['CreationDate'],
            'persist': set_persist,
            'build_method': set_buildmethod,
            'snapshot_id': snapshot_data
        }
for item in image_data:
    print "id: %s" % (item)
    # print "test: %s" % (image_data[item])
    print "\tname: %s" % (image_data[item]['name'])
    print "\tdate: %s" % (image_data[item]['date'])
    print "\tpersist: %s" % (image_data[item]['persist'])
    print "\tbuild_method: %s" % (image_data[item]['build_method'])
    for snap in image_data[item]['snapshot_id']:
        print "\t\tsnapshot_id: %s" % (snap)
