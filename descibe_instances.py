#!/usr/bin/env python

import sys
from boto3.session import Session

from get_nodes_in_region import getNodes

def listNodes(pattern, region):
    session = Session()
    ec2 = session.resource('ec2', region_name=region)
    filters = [{'Name':'tag:Name', 'Values':[pattern]}]
    print 'Nodes matching Name tag pattern', pattern
    index = 0
    for instance in ec2.instances.filter(Filters=filters):
        index = index + 1
        name = 'Unknown'
        for tag in instance.tags:
            if tag['Key'] == 'Name':
                name = tag['Value']
                break
        fmt = '{:3})  {}   {}   {}'
        print fmt.format(index, name, instance.id, instance.private_ip_address)


def usage():
    print 'USAGE: idesc <pattern> [region]'
    sys.exit(1)

if __name__ == "__main__":
    region = "us-east-1"

    argc = len(sys.argv)

    if argc < 2:
        usage()

    if argc > 2:
        region = sys.argv[2]

    listNodes(sys.argv[1], region)


