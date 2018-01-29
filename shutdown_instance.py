import logging
import argparse
import boto3
import time
from datetime import datetime, timedelta


volume_metric_mininum = 300
volume_data = {}
instance_data = {}
current_time = int(round(time.time()))
full_day = 86400
today = datetime.now()
tomorrow = datetime.now() + timedelta(days=1)
yesterday = datetime.now() - timedelta(days=1)
two_weeks = datetime.now() - timedelta(days=14)
four_weeks = datetime.now() - timedelta(days=28)
thirty_days = datetime.now() - timedelta(days=30)


class Metrics(object):
    def __init__(self, client, dry_run):
        self.client = client
        self.dry_run = dry_run

    def is_active(self, instance_id):
        '''
            Determine if Volume is attached to running instance
        '''
        logging.critical("\tChecking for disk usage on running host: %s" % (instance_id))
        if instance_id in instance_data and instance_data[instance_id]['state'] == 'running':
            return True
        return False

    def is_candidate(self, volume_id, instance_id):
        '''
            Make sure the volume is candidate for delete
        '''
        if Metrics(self.client, self.dry_run).is_active(instance_id):
            metrics = Metrics(self.client, self.dry_run).metrics(volume_id)
            if len(metrics) > 0:
                for metric in metrics:
                    if metric['Minimum'] < volume_metric_mininum:
                        logging.critical("\tInactive Volume: (metric:%i, instance:%s volume:%s)" % (metric['Minimum'], instance_id, volume_id))
                        return True
                    else:
                        logging.critical("\tActive Volume - Ignoring for deletion: (metric:%i, instance:%s volume:%s)" % (metric['Minimum'], instance_id, volume_id))
                        return False
            else:
                logging.critical("metrics not returned")
                return False
        else:
            logging.critical("%s not active on %s" % (volume_id, instance_id))
            return True

    def metrics(self, volume_id):
        '''
            Get volume idle time on an individual volume over `start_date` to today
        '''
        self.volume_metrics_data = self.client.get_metric_statistics(
            Namespace='AWS/EBS',
            MetricName='VolumeIdleTime',
            Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
            Period=3600,
            StartTime=two_weeks,
            EndTime=today,
            Statistics=['Minimum'],
            Unit='Seconds'
        )
        logging.debug("\t\tReturning datapoints: %s" % (self.volume_metrics_data['Datapoints'][0]['Minimum']))
        return self.volume_metrics_data['Datapoints']


class conn(object):
    def ec2(self, region):
        '''
            Class to broker connection to aws
        '''
        logging.critical("Initiating Connection to service('cloudwatch') in region(%s)" % (region))
        self.client = boto3.client('ec2', region_name=region)
        return self.client

    def cloudwatch(self, region):
        '''
            Class to broker connection to aws
        '''
        logging.critical("Initiating Connection to service('cloudwatch') in region(%s)" % (region))
        self.client = boto3.client('cloudwatch', region_name=region)
        return self.client


class Instance():
    def __init__(self, client, dry_run):
        self.client = client
        self.dry_run = dry_run

    def stop_instance(self, instance):
        self.client.stop_instances(
            InstanceIds=[instance],
            DryRun=True,
        )
        return True

    def find(self, instance):
        self.describe_instances = sorted(
            self.client.describe_instances(
                Filters=[{
                    'Name': 'instance-state-name',
                    'Values': ['running', 'stopped']
                }, {
                    'Name': 'instance-id',
                    'Values': [instance]
                }]
            )['Reservations']
        )
        for item in self.describe_instances:
            instance_data[item['Instances'][0]['InstanceId']] = {
                'id': item['Instances'][0]['InstanceId'],
                'state': item['Instances'][0]['State']['Name'],
                'type': item['Instances'][0]['InstanceType'],
                'private_dns': item['Instances'][0]['PrivateDnsName'],
                'launch_time': item['Instances'][0]['LaunchTime'],
                'image_id': item['Instances'][0]['ImageId'],
                'virt': item['Instances'][0]['VirtualizationType'],
                'volumes': []
            }
        return True


class Volume(object):
    def __init__(self, client, dry_run):
        self.client = client
        self.dry_run = dry_run

    def find(self, cloudwatch_client, instance):
        '''
            find_volumes function
        '''
        logging.critical("\n*** Retrieving volumes")
        volumes = sorted(
            self.client.describe_volumes(
                Filters=[{
                    'Name': 'attachment.instance-id',
                    'Values': [instance]
                }]
            )['Volumes'],
            key=lambda x: (
                x['VolumeId']
            ),
            reverse=True
        )
        for volume in volumes:
            print "Checking on volume: %s" % (volume['VolumeId'])
            if Metrics(cloudwatch_client, self.dry_run).is_candidate(volume['VolumeId'], instance):
                Instance(self.client, self.dry_run).stop_instance(instance)


def handler(event, context):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--region',
        choices=[
            "us-east-1",
            "us-west-1",
            "us-west-2",
            "ap-southeast-1"
            # etc
        ],
        nargs='?',
        metavar='',
        default=event['region'],
        help="region",
    )
    parser.add_argument(
        '--instance',
        nargs='?',
        metavar='',
        default=event['instance-id'],
        help="instance-id",
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=event['dry-run'],
        help="DryRun"
    )
    args = parser.parse_args()
    if not args.region or not args.instance:
        print parser.print_help()
        exit(3)
    cloudwatch_client = conn().cloudwatch(args.region)
    ec2_client = conn().ec2(args.region)
    Instance(ec2_client, args.dry_run).find(args.instance)
    Volume(ec2_client, args.dry_run).find(cloudwatch_client, args.instance)