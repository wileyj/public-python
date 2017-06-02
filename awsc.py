#!/usr/bin/env python

import sys
import subprocess
import readline
import os
from boto3.session import Session

from get_nodes_in_region import getNodes

WEST_1 = 'us-west-1'
WEST_2 = 'us-west-2'
EAST = 'us-east-1'

DEFAULT_APPLICATION = 'app'
DEFAULT_ENV = 'dev'
DEFAULT_REGION = WEST_1

BASTION = 'bastion.local.com'
USER = 'ec2-user'

network = {
    'app' : {
        'dev' : WEST_2,
        'staging' : WEST_2,
        'prod' : WEST_1
    },
    'steppers' : {
        'dev' : WEST_2,
        'staging' : WEST_2,
        'prod' : WEST_1
    }
}


def listNodes(app, env):
    region = network[app][env]
    session = Session()
    ec2 = session.resource('ec2', region_name=region)
    filters = [{'Name':'tag:Name', 'Values':['-'.join([app, env, '*'])]}]

    print 'Listing nodes for', env, app, '( region:', region, ') ...'
    base = ec2.instances.filter(Filters=filters)
    index = 0
    ips = []
    for instance in base:
        index = index + 1
        name = 'Unknown'
        for tag in instance.tags:
            if tag['Key'] == 'Name':
                name = tag['Value']
                break
        fmt = '{:3})  {}   {}   {}'
        print fmt.format(index, name, instance.id, instance.private_ip_address)
        ips.append(instance.private_ip_address)

    return ips


def getIntInRange(message, high, low=0):
    while True:
        rawIndex = None
        try:
            rawIndex = raw_input(message).strip()
        except EOFError:
            print '(EOF)'
            sys.exit(0)
        except KeyboardInterrupt:
            print '(Broken)'
            sys.exit(0)

        if rawIndex == None or rawIndex == "":
            print 'No input'
            continue

        try:
            index = int(rawIndex)
            if index >= low and index <= high:
                return index
            print index, 'not in range.'
        except ValueError:
            print "Couldn't derive int from", rawIndex


def connectToHost(ip):
    command = 'ssh -A -t {}@{} ssh -A -t {}'.format(USER, BASTION, ip)
    os.system(command)


if __name__ == "__main__":
    app = DEFAULT_APPLICATION
    env = DEFAULT_ENV

    argc = len(sys.argv)

    if argc > 1:
        app = sys.argv[1]

    if argc > 2:
        env = sys.argv[2]

    ips = listNodes(app, env)
    selected = getIntInRange('Select a host by index and hit enter: ', len(ips))
    selected = selected - 1
    print 'Connecting to host at', ips[selected]
    connectToHost(ips[selected])


