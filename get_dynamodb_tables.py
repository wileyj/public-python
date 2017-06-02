import boto3
import os

os.environ["AWS_PROFILE"] = "ddb_staging"
sts_client = boto3.client('sts')
account_id = '000000'
iam_role = 'testrole'
assumedRoleObject = sts_client.assume_role(
    RoleArn='arn:aws:iam::'+account_id+':role/'+iam_role,
    RoleSessionName='AssumePocRole',
    DurationSeconds=900)
print assumedRoleObject['Credentials']['AccessKeyId']
print assumedRoleObject['Credentials']['SecretAccessKey']
print assumedRoleObject['Credentials']['SessionToken']
credentials = assumedRoleObject['Credentials']
client = boto3.client(
    'dynamodb',
    region_name='us-east-1',
    aws_access_key_id = credentials['AccessKeyId'],
    aws_secret_access_key = credentials['SecretAccessKey'],
    aws_session_token = credentials['SessionToken'],
)
response_list = client.list_tables()
print response_list
response_describe = client.describe_table(
    TableName='devices_staging'
)
print response_describe
