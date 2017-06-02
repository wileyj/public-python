import boto3
import datetime

ec2_client = boto3.client('ec2', region_name='us-east-1')
response = ec2_client.describe_instances(
    Filters=[{
        'Name': 'tag:Name',
        'Values': ['<name>']
    }]
)

for reservation in (response["Reservations"]):
    print "r_id: %s " % (reservation["ReservationId"])
    for instance in reservation["Instances"]:
        print instance["InstanceId"]
    print len(reservation)
