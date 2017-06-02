#!/usr/bin/env python
import httplib
import boto3
import json
import logging
log = logging.getLogger(__name__)

domain = "local.com"
regions = {
    "us-east-1" : "use1",
    "us-west-1" : "usw1",
    "us-west-2" : "usw2"
}
env_short = {
    "production": "prd",
    "dev": "dev",
    "qa": "qa",
    "staging": "stg",
    "core": "core",
    "bastion": "b",
    "app": "app",
    "web": "web",
    "db": "db"
}
def _call_aws(url):
    conn = httplib.HTTPConnection("169.254.169.254", 80, timeout=1)
    conn.request('GET', url)
    return conn.getresponse().read()

def _ec2_network(data):
    ec2_network_grain = {}
    nics = []
    ec2_network_grain["private_ip_address"] = data['NetworkInterfaces'][0]['PrivateIpAddress']
    ec2_network_grain["private_dns_name"] = data['NetworkInterfaces'][0]['PrivateDnsName']
    ec2_network_grain["description"] = data['NetworkInterfaces'][0]['Description']
    ec2_network_grain["first_two_octets"] = data['NetworkInterfaces'][0]['PrivateIpAddress'].split(".")[0]+"."+data['NetworkInterfaces'][0]['PrivateIpAddress'].split(".")[1]
    ec2_network_grain["gateway"] = data['NetworkInterfaces'][0]['PrivateIpAddress'].split(".")[0]+"."+data['NetworkInterfaces'][0]['PrivateIpAddress'].split(".")[1]+".0.2"
    for index, nic in enumerate(data['NetworkInterfaces'][0]['PrivateIpAddresses'], start=0):
        info = {
            "Nic": {
                "PrivateIpAddress": nic['PrivateIpAddress'],
                "PrivateDnsName": nic['PrivateDnsName'],
                "PublicIp": nic['Association']['PublicIp'],
                "PublicDnsName": nic['Association']['PublicDnsName'],
                "public": {
                    "PublicIp": nic['Association']['PublicIp'],
                    "PublicDnsName": nic['Association']['PublicDnsName']
                }
            }
        }
        nics.append(info)
    return ec2_network_grain

def _ec2_disk(data):
    ec2_disk_grain = {}
    ec2_disk_grain['RootDeviceType'] = data['RootDeviceType']
    ec2_disk_grain['RootDeviceName'] = data['RootDeviceName']
    ec2_disk_grain['EbsOptimized'] = data['EbsOptimized']
    disks = []
    for index, ebs in enumerate(data['BlockDeviceMappings'], start=0):
        short = ebs['DeviceName'].split("/")[2]
        info = {
            ebs['DeviceName']: {
                "DeviceName": ebs['DeviceName'],
                "DeviceShort": short,
                "Status": ebs['Ebs']['Status'],
                "DeleteOnTermination": ebs['Ebs']['DeleteOnTermination'],
                "VolumeId": ebs['Ebs']['VolumeId'],
                "AttachTime": str(ebs['Ebs']['AttachTime'])
            }
        }
        disks.append(info)
    ec2_disk_grain["block_device_mappings"] = disks
    return ec2_disk_grain

def _ec2_tags(data):
    ec2_tag_grain = {}
    for tag in data:
        ec2_tag_grain[tag['Key']] = tag['Value']
    # for later.....
    #     if tag['Key'] == "Name":
    #         ec2_tag_grain["business_unit"] = tag['Value'].split("-")[0]
    #         ec2_tag_grain["role"] = tag['Value'].split("-")[1]
    #         ec2_tag_grain["region_short"] = tag['Value']
    #         ec2_tag_grain["role"] = tag['Value'].split("-")[1]
    #         if tag['Value'].split("-")[2]:
    #             ec2_tag_grain["host_num"] = tag['Value'].split("-")[2]
    #         else:
    #             ec2_tag_grain["host_num"] = "000"
    #         ec2_tag_grain["name"] = tag['Value'].lower()
    #     elif tag['Key'] == "Environment":
    #         ec2_tag_grain["environment"] = tag['Value'].lower()
    #         try:
    #             if env_short[tag['Value']]:
    #                 env_name = env_short[tag['Value'].lower()]
    #             else:
    #                 env_name = "default"
    #         except Exception:
    #             print "Defined ENV not found %s" % (tag['Value'])
    #     elif tag['Key'] == "Region":
    #         ec2_tag_grain["region"] = (tag['Value'].lower())
    #     elif tag['Key'] == "SiteName":
    #         ec2_tag_grain["sitename"] = tag['Value'].lower()
    #     elif tag['Key'] == "elasticbeanstalk:environment-id":
    #         ec2_tag_grain["elasticbeanstalk_id"] = tag['Value']
    #         beanstalk = 1
    #     elif tag['Key'] == "elasticbeanstalk:environment-name":
    #         ec2_tag_grain["elasticbeanstalk_name"] = tag['Value']
    #     else:
    #         ec2_tag_grain[tag['Key']] = tag['Value']
    # ec2_tag_grain["region_short"] = regions[ec2_region].lower()
    # if beanstalk == 1:
    #     ec2_tag_grain["hostname_full"] = ec2_tag_grain["business_unit"].lower() + "-" + ec2_tag_grain["role"].lower() + "-" + ec2_tag_grain["host_num"] + "-" + ec2_tag_grain["instance_id"] + "." + env_name.lower() + "." + "." + regions[ec2_region].lower() + "." + domain.lower()
    # else:
    #     ec2_tag_grain["hostname_full"] = ec2_tag_grain["business_unit"].lower() + "-" + ec2_tag_grain["role"].lower() + "-" + ec2_tag_grain["host_num"] + "." + env_name.lower() + "." + regions[ec2_region].lower() + "." + domain.lower()
    # ec2_tag_grain["region_searchpath"] = regions[ec2_region]+"."+domain
    return ec2_tag_grain

def _ec2_info(data):
    ec2_info_grain = {}
    sg = []
    for index, sg in enumerate(data['SecurityGroups'], start=0):
        sg.append(sg['GroupId'])
    ec2_info_grain['LaunchTime'] = str(data['LaunchTime'])
    ec2_info_grain['VpcId'] = data['VpcId']
    ec2_info_grain['InstanceId'] = data['InstanceId']
    ec2_info_grain['ImageId'] = data['ImageId']
    ec2_info_grain['KeyName'] = data['KeyName']
    ec2_info_grain['SecurityGroups'] = sg
    ec2_info_grain['SubnetId'] = data['SubnetId']
    ec2_info_grain['InstanceType'] = data['InstanceType']
    ec2_info_grain['Architecture'] = data['Architecture']
    ec2_info_grain['IamInstanceProfile'] = data['IamInstanceProfile']['Arn']
    return ec2_info_grain

# if __name__ == "__main__":
def function():
    try:
        instance_id = str(_call_aws("/latest/meta-data/instance-id/"))
        region = str(json.loads(_call_aws("/latest/dynamic/instance-identity/document"))['region'])
    except:
        exit(1)

    ec2_client = boto3.client('ec2', region_name='us-east-1')
    instances = ec2_client.describe_instances(
        Filters=[{
            'Name': 'instance-id',
            'Values': [instance_id]
        }]
    )['Reservations'][0]['Instances']
    grains = {}
    network = _ec2_network(instances[0])
    disks = _ec2_disk(instances[0])
    info = _ec2_info(instances[0])
    tags = _ec2_info(instances[0]['Tags'])

        # grains.update({'ec2-tags': tags})
    grains.update({'ec2-info': info})
    grains.update({'ec2-disks': disks})
    grains.update({'ec2-network': network})
    # print {'ec2-data': grains}
    return {'ec2-data': grains}
