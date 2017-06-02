import boto3
import datetime

ec2_client = boto3.client('ec2', region_name='us-east-1')
images = ec2_client.describe_images(
    Filters=[
        {'Name': 'root-device-type', 'Values': ['ebs']},
        {'Name': 'name', 'Values': ['ubuntu*16*server*']},
#        {'Name': 'image-id', 'Values': ['ami-3af71c2'] },
        {'Name': 'virtualization-type', 'Values': ['hvm']},
#        {'Name': 'owner-alias', 'Values': ['']},
        {'Name': 'owner-id', 'Values': ['099720109477']}
    ]
)
image_list = []
for image in images['Images']:
 #   print image
    image_list.append(image)
    image_list.sort( key=lambda x:datetime.datetime.strptime(x['CreationDate'], '%Y-%m-%dT%H:%M:%S.000Z'))
image_id = image_list[len(image_list)-1]['ImageId']
print "image_id: %s" % (image_id)
for x in image_list:
    if x['ImageId'] == image_id:
        print x
