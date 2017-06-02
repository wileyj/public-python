import boto3
import datetime
import sys

if len(sys.argv) == 2:
    arg = sys.argv[1]+'*'
else:
    print "no arg defined"
    sys.exit(1)

ec2_client = boto3.client('ec2', region_name='us-east-1')
response = ec2_client.describe_instances(
    Filters=[{
        'Name': 'instance-state-name',
        'Values': ['running', 'stopped']
    },{
        'Name': 'tag:Name',
        'Values': [arg]
    }]
)
for num, reservation in enumerate(response["Reservations"][0::]):
    for val, instance in enumerate(reservation['Instances'][0::]):
        print instance['PrivateIpAddress']
