#!/usr/bin/env python
""" docstring """
# TODO: check for existing staging DB. if exists, either rename or delete

import argparse
import logging
import datetime
import time
import boto3

epoch = time.time()
timestamp = datetime.datetime.utcnow().isoformat()

class Unbuffered(object):
    """ Class to push stdout buffer to screen immediately """
    def __init__(self, stream):
        """ docstring for linter """
        self.stream = stream
    def write(self, data):
        """ docstring for linter """
        self.stream.write(data)
        self.stream.flush()
    def __getattr__(self, attr):
        """ docstring for linter """
        return getattr(self.stream, attr)

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

def get_instances(db, name):
    """ docstring """
    describe_dbs = rds_client.describe_db_instances(
        DBInstanceIdentifier=db
    )
    db_dict = {}
    db_sg_groups = []
    if len(describe_dbs['DBInstances']) > 0 and len(describe_dbs['DBInstances']) < 2:
        logging.debug("LicenseModel: %s" % (describe_dbs['DBInstances'][0]['LicenseModel']))
        logging.debug("EnhancedMonitoringResourceArn: %s" % (describe_dbs['DBInstances'][0]['EnhancedMonitoringResourceArn']))
        logging.debug("DBInstanceIdentifier: %s" % (describe_dbs['DBInstances'][0]['DBInstanceIdentifier']))
        logging.debug("New DBInstanceIdentifier: %s" % (name))
        logging.debug("AllocatedStorage: %s" % (describe_dbs['DBInstances'][0]['AllocatedStorage']))
        logging.debug("BackupRetentionPeriod: %s" % (describe_dbs['DBInstances'][0]['BackupRetentionPeriod']))
        logging.debug("DBName: %s" % (describe_dbs['DBInstances'][0]['DBName']))
        logging.debug("EngineVersion: %s" % (describe_dbs['DBInstances'][0]['EngineVersion']))
        logging.debug("AvailabilityZone: %s" % (describe_dbs['DBInstances'][0]['AvailabilityZone']))
        logging.debug("StorageType: %s" % (describe_dbs['DBInstances'][0]['StorageType']))
        logging.debug("Iops: %s" % (describe_dbs['DBInstances'][0]['Iops']))
        logging.debug("StorageEncrypted: %s" % (describe_dbs['DBInstances'][0]['StorageEncrypted']))
        logging.debug("DBInstanceClass: %s" % (describe_dbs['DBInstances'][0]['DBInstanceClass']))
        logging.debug("PubliclyAccessible: %s" % (describe_dbs['DBInstances'][0]['PubliclyAccessible']))
        logging.debug("MasterUsername: %s" % (describe_dbs['DBInstances'][0]['MasterUsername']))
        logging.debug("CopyTagsToSnapshot: %s" % (describe_dbs['DBInstances'][0]['CopyTagsToSnapshot']))
        logging.debug("Engine: %s" % (describe_dbs['DBInstances'][0]['Engine']))
        logging.debug("MultiAZ: %s" % (describe_dbs['DBInstances'][0]['MultiAZ']))
        logging.debug("DBSubnetGroupName: %s" % (describe_dbs['DBInstances'][0]['DBSubnetGroup']['DBSubnetGroupName']))
        logging.debug("VpcId: %s" % (describe_dbs['DBInstances'][0]['DBSubnetGroup']['VpcId']))
        logging.debug("OptionGroupName: %s" % (describe_dbs['DBInstances'][0]['OptionGroupMemberships'][0]['OptionGroupName']))
        logging.debug("DBParameterGroupName: %s" % (describe_dbs['DBInstances'][0]['DBParameterGroups'][0]['DBParameterGroupName']))
        logging.debug("MonitoringRoleArn: %s" % (describe_dbs['DBInstances'][0]['MonitoringRoleArn']))
        for index, this in enumerate(describe_dbs['DBInstances'][0]['VpcSecurityGroups'], start=0):
            logging.debug("\tGroup: %i %s " % (index, this['VpcSecurityGroupId']))
            db_sg_groups.append(this['VpcSecurityGroupId'])
        logging.debug("\tUsing Snapshot: %s" % (get_snapshot(db)))

        db_dict['LicenseModel'] = describe_dbs['DBInstances'][0]['LicenseModel']
        db_dict['DBInstanceIdentifier'] = name
        db_dict['AllocatedStorage'] = describe_dbs['DBInstances'][0]['AllocatedStorage']
        db_dict['BackupRetentionPeriod'] = describe_dbs['DBInstances'][0]['BackupRetentionPeriod']
        db_dict['DBName'] = describe_dbs['DBInstances'][0]['DBName']
        db_dict['EngineVersion'] = describe_dbs['DBInstances'][0]['EngineVersion']
        db_dict['AvailabilityZone'] = describe_dbs['DBInstances'][0]['AvailabilityZone']
        db_dict['StorageType'] = describe_dbs['DBInstances'][0]['StorageType']
        db_dict['Iops'] = describe_dbs['DBInstances'][0]['Iops']
        db_dict['StorageEncrypted'] = describe_dbs['DBInstances'][0]['StorageEncrypted']
        db_dict['DBInstanceClass'] = describe_dbs['DBInstances'][0]['DBInstanceClass']
        db_dict['PubliclyAccessible'] = describe_dbs['DBInstances'][0]['PubliclyAccessible']
        db_dict['MasterUsername'] = describe_dbs['DBInstances'][0]['MasterUsername']
        db_dict['CopyTagsToSnapshot'] = describe_dbs['DBInstances'][0]['CopyTagsToSnapshot']
        db_dict['Engine'] = describe_dbs['DBInstances'][0]['Engine']
        db_dict['MultiAZ'] = describe_dbs['DBInstances'][0]['MultiAZ']
        db_dict['DBSubnetGroupName'] = describe_dbs['DBInstances'][0]['DBSubnetGroup']['DBSubnetGroupName']
        db_dict['VpcId'] = describe_dbs['DBInstances'][0]['DBSubnetGroup']['VpcId']
        db_dict['VpcSecurityGroupIds'] = db_sg_groups
        db_dict['SnapShot'] = get_snapshot(db)
        db_dict['OptionGroupName'] = describe_dbs['DBInstances'][0]['OptionGroupMemberships'][0]['OptionGroupName']
        db_dict['DBParameterGroupName'] = describe_dbs['DBInstances'][0]['DBParameterGroups'][0]['DBParameterGroupName']
        db_dict['EnhancedMonitoringResourceArn'] = describe_dbs['DBInstances'][0]['EnhancedMonitoringResourceArn']
        db_dict['MonitoringRoleArn'] = describe_dbs['DBInstances'][0]['MonitoringRoleArn']
        create_instance(db_dict, name)

    else:
        print "the wrong number of instances was returned for %s: %i" % (db, len(describe_dbs['DBInstances']))
        exit(3)
    return 0

def get_snapshot(db):
    """ docstring """
    describe_snapshots = rds_client.describe_db_snapshots(
        DBInstanceIdentifier=db
    )
    snapshot_list = []
    for item in describe_snapshots['DBSnapshots']:
        # print "%s" % (item['DBInstanceIdentifier'])
        # print "\tVPC:                  %s" % (item['VpcId'])
        # print "\tSnapshot Time:        %s" % (item['SnapshotCreateTime'])
        # print "\tPercentProgress:      %s" % (item['PercentProgress'])
        # print "\tAllocatedStorage:     %s" % (item['AllocatedStorage'])
        # print "\tMasterUsername:       %s" % (item['MasterUsername'])
        # print "\tDBSnapshotIdentifier: %s" % (item['DBSnapshotIdentifier'])
        # print "\tDBInstanceIdentifier: %s\n" % (item['DBInstanceIdentifier'])
        snapshot_list.append(item)
    if len(snapshot_list) > 0:
        snapshot_list.sort(key=lambda x: x['SnapshotCreateTime'])
        return snapshot_list[len(snapshot_list)-1]['DBSnapshotIdentifier']
    else:
        return 1

def create_instance(db_dict, name):
    """ docstring """
    rds_client.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier=db_dict['DBInstanceIdentifier'],
        DBSnapshotIdentifier=db_dict['SnapShot'],
        DBInstanceClass=db_dict['DBInstanceClass'],
        Port=5432,
        AvailabilityZone=db_dict['AvailabilityZone'],
        DBSubnetGroupName=db_dict['DBSubnetGroupName'],
        MultiAZ=False,
        PubliclyAccessible=db_dict['PubliclyAccessible'],
        AutoMinorVersionUpgrade=True,
        LicenseModel=db_dict['LicenseModel'],
        Engine=db_dict['Engine'],
        Iops=db_dict['Iops'],
        OptionGroupName=db_dict['OptionGroupName'],
        Tags=[{
            'Key': 'Name',
            'Value': db_dict['DBInstanceIdentifier'],
        }, {
            'Key': 'Region',
            'Value': 'us-east-1'
        }, {
            'Key': 'Environment',
            'Value': 'staging'
        }],
        StorageType=db_dict['StorageType'],
        CopyTagsToSnapshot=True,
    )
    waiter = rds_client.get_waiter('db_instance_available')
    waiter.wait(
        DBInstanceIdentifier=name
    )
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--region",
        metavar="",
        default="us-east-1",
        help="AWS Region"
    )
    parser.add_argument(
        "--db",
        metavar="",
        default="",
        help="RDS Instance to Clone"
    )
    parser.add_argument(
        "--name",
        metavar="",
        default="",
        help="New RDS Name"
    )
    parser.add_argument(
        "-v",
        metavar="",
        nargs="?",
        action=VAction,
        dest="verbose"
    )
    args = parser.parse_args()
    if args.verbose == 4:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose == 3:
        logging.basicConfig(level=logging.ERROR)
    elif args.verbose == 2:
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO)
    rds_client = boto3.client('rds', region_name=args.region)
    get_instances(args.db, args.name)
