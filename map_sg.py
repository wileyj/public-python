#!/usr/bin/env python
# grab all subnets and vpcs, push into dict as:
# 'subnet': 'name of item from tag'
# and display that along with the ip reprentation from the sg output
""" script to map security groups """
from boto3.session import Session

region = "us-east-1"
session = Session()
ec2 = session.resource('ec2', region_name=region)
sg_map = {}
def getInstance(cidr):
    """ Retrieve Host of IP """
    to_return = ""
    if cidr.split("/", 1)[1] == "32":
        ip = str(cidr.split("/", 1)[0]).strip('')
        running_instance = ec2.instances.filter(
            Filters=[{
                'Name': 'private-ip-address',
                'Values': [ip]
            }, {
                'Name':'instance-state-name',
                'Values': ['running']
            }]
        )
        for  instance in running_instance:
            for tag in instance.tags:
                if tag['Key'] == "Name":
                    to_return = tag['Value']
    else:
        to_return = cidr
        # return "1 - %s" % (cidr)
    if to_return == "":
        return cidr
    else:
        return to_return

def getRules(sg, name):
    """ Retrieve the Rules of SG """
    group = ec2.SecurityGroup(sg)
    count = 0
    print "%s (%s)" % (name, sg)
    for item in group.ip_permissions:
        cidr_len = len(item['IpRanges'])
        group_len = len(item['UserIdGroupPairs'])
        if item['IpProtocol'] == '-1':
            ports = "ALL\t\t\t"
        else:
            if item['FromPort'] == item['ToPort']:
                ports = "port1(%s)\t\t" % (item['FromPort'])
            elif item['FromPort'] < 10 and  item['ToPort'] < 10:
                ports = "port2(%s - %s)\t" % (item['FromPort'],item['ToPort'])
            elif item['FromPort'] > 10 and item['FromPort'] < 100 and item['ToPort'] > 10 and item['ToPort'] < 100:
                ports = "port2(%s - %s)\t" % (item['FromPort'],item['ToPort'])
            else:
                ports = "port3(%s - %s)" % (item['FromPort'],item['ToPort'])
        if group_len > 0:
            for rule in item['UserIdGroupPairs']:
                count = count+1
                try:
                    print "\t%s\t-->\t(%s - %s)" % (ports, rule['GroupId'], sg_map[rule['GroupId']])
                except KeyError:
                    print "\t%s\t-->\t(%s - 'missing')" % (ports, rule['GroupId'])

        if cidr_len > 0:
            for rule in item['IpRanges']:
                count = count+1
                print "\t%s\t-->\t(%s)" % (ports, getInstance(rule['CidrIp']))
    print ""
    return 0

def getSg():
    """ Retrieve the SG's """
    s_groups = ec2.security_groups.filter()
    for group in s_groups:
        # print "Name: %s ( %s )" % (group.group_name, group.id)
        sg_map[group.id] = group.group_name
    for key, val in sg_map.iteritems():
        getRules(key, val)

if __name__ == "__main__":
    getSg()
