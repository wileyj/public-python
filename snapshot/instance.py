from config import Global
import logging
from logger import Logger

Logger()


class Instance():
    def __init__(self, client):
        self.client = client

    def find(self, env, instance):
        '''
            find_instances function
        '''
        logging.critical("*** Retrieving instances")
        logging.critical("env: %s" % (env))
        logging.critical("instance: %s" % (instance))
        Global.instances_vpc = sorted(
            self.client.describe_instances(
                Filters=[{
                    'Name': 'vpc-id',
                    'Values': ['*']
                }, {
                    'Name': 'instance-state-name',
                    'Values': ['running', 'stopped']
                }, {
                    'Name': 'tag:Environment',
                    'Values': [env]
                }]
            )['Reservations'],
            key=lambda x: (
                x['Instances'][0]['LaunchTime'],
                x['Instances'][0]['InstanceId']
            ),
            reverse=True
        )
        logging.critical("Total vpc instances: %i" % (len(Global.instances_vpc)))
        if not instance:
            instances_all = sorted(
                self.client.describe_instances(
                    Filters=[{
                        'Name': 'instance-state-name',
                        'Values': ['running', 'stopped']
                    }, {
                        'Name': 'tag:Environment',
                        'Values': [env]
                    }]
                )['Reservations'],
                key=lambda x: (
                    x['Instances'][0]['LaunchTime'],
                    x['Instances'][0]['InstanceId']
                ),
                reverse=True
            )
            logging.critical("if Total instances_all: %i" % (len(instances_all)))
        else:
            instances_all = sorted(
                self.client.describe_instances(
                    Filters=[{
                        'Name': 'instance-state-name',
                        'Values': ['running', 'stopped']
                    }, {
                        'Name': 'instance-id',
                        'Values': [instance]
                    }]
                )['Reservations'],
                key=lambda x: (
                    x['Instances'][0]['LaunchTime'],
                    x['Instances'][0]['InstanceId']
                ),
                reverse=True
            )
            logging.critical("else Total instances_all: %i" % (len(instances_all)))
        try:
            if len(instances_all) < 1:
                logging.debug("instances_all returned zero results...")
                logging.debug(instances_all)
        except:
            pass
        list_vpc = [item for item in Global.instances_vpc]
        list_all = [item for item in instances_all]
        instance_without_vpc = [item for item in instances_all if item not in list_vpc]
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
            except:
                t_vpc = "None"
            try:
                if item['Instances'][0]['Platform']:
                    platform = item['Instances'][0]['Platform']
            except:
                platform = "Linux"
            try:
                if item['Instances'][0]['PrivateIpAddress']:
                    private_ip_address = item['Instances'][0]['PrivateIpAddress']
            except:
                private_ip_address = "Undefined"
            try:
                if item['Instances'][0]['SubnetId']:
                    subnet_id = item['Instances'][0]['SubnetId']
            except:
                subnet_id = "Undefined"
            Global.instance_data[item['Instances'][0]['InstanceId']] = {
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
                if not dry_run:
                    client.create_tags(
                        # DryRun=True,
                        Resources=[item['Instances'][0]['InstanceId']],
                        Tags=[{
                            'Key': 'Delete',
                            'Value': 'True'
                        }]
                    )
            for volume in item['Instances'][0]['BlockDeviceMappings']:
                Global.instance_data[item['Instances'][0]['InstanceId']]['volumes'].append(volume['Ebs']['VolumeId'])
            try:
                Global.map_images[item['Instances'][0]['ImageId']] = {
                    'imaged_id': item['Instances'][0]['ImageId'],
                    'instance_id': [item['Instances'][0]['InstanceId']],
                }
            except:
                Global.map_images[item['Instances'][0]['ImageId']]['instance_id'].append(item['Instances'][0]['InstanceId'])
        logging.critical("\t Total VPC Instances: %s" % (len(list_vpc)))
        logging.critical("\t Total Instances: %s" % (len(list_all)))
        logging.critical("\t Total Classic Instances: %i" % (len(instance_without_vpc)))
        logging.critical("\t Total Running Instances: %i" % (running_count))
        logging.critical("\t Total Stopped Instances: %i" % (stopped_count))
        logging.critical("\t Total Mapped Instances: %i" % (len(Global.map_images)))
        logging.critical("\t Items in instance_data dict: %i" % (len(Global.instance_data)))
        return True
