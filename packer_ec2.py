#!/usr/bin/env python
""" docstring """
# Naming:
# ord-amzn-<disk>-<virt>_<prefix>-<platform>-<type>
#   local-amzn-single-hvm_packer-base-ec2
#   local-amzn-single-hvm_packer-ecs-beanstalk
#
#
# python packer_ec2.py --prefix packer --platform base  --type beanstalk --disk multidisk  --virt hvm --instance t2.micro
# python packer_ec2.py --prefix packer --platform base  --type beanstalk --disk multidisk  --virt pv --instance t1.micro
# python packer_ec2.py --prefix packer --platform base  --type beanstalk --disk singledisk --virt hvm --instance t2.micro
# python packer_ec2.py --prefix packer --platform base  --type beanstalk --disk singledisk --virt pv --instance t1.micro
# python packer_ec2.py --prefix packer --platform node --type beanstalk --disk multidisk  --virt hvm --instance t2.micro
# python packer_ec2.py --prefix packer --platform node --type beanstalk --disk multidisk  --virt pv --instance t1.micro
# python packer_ec2.py --prefix packer --platform node --type beanstalk --disk singledisk --virt hvm --instance t2.micro
# python packer_ec2.py --prefix packer --platform node --type beanstalk --disk singledisk --virt pv --instance t1.micro

# python packer_ec2.py --prefix packer --platform base  --type ec2 --disk multidisk --virt hvm --instance t2.micro
# python packer_ec2.py --prefix packer --platform base  --type ec2 --disk multidisk --virt pv --instance t1.micro
# python packer_ec2.py --prefix packer --platform base  --type ec2 --disk singledisk --virt hvm --instance t2.micro --vpc-id vpc-93d7a6f6 --subnet-id subnet-3d5b2207 --region us-east-1
# rm -rf /var/tmp/*[0-9]* && python packer_ec2.py --os coreos --ssh-user ec2-user --vpc-id vpc-93d7a6f6 --subnet-id subnet-3d5b2207 --instance-type t2.micro --virt hvm --prefix packer --disk single --stage dev --type base --region us-east-1  --tag latest

# python packer_ec2.py --prefix packer --platform base  --type ec2 --disk singledisk --virt pv --instance t1.micro

# python packer_ec2.py --prefix packer --platform ecs  --type ec2 --disk multidisk --virt hvm --instance t2.micro
# python packer_ec2.py --prefix packer --platform ecs  --type ec2 --disk singledisk --virt hvm --instance t2.micro
# python packer_ec2.py --prefix packer --platform ecs  --type beanstalk --disk multidisk --virt pv --instance t1.micro
# python packer_ec2.py --prefix packer --platform ecs  --type beanstalk --disk multidisk --virt hvm --instance t2.micro
# python packer_ec2.py --prefix packer --platform ecs  --type beanstalk --disk singledisk --virt pv --instance t1.micro
# python packer_ec2.py --prefix packer --platform ecs  --type beanstalk --disk singledisk --virt hvm --instance t2.micro

# TODO
#   - copy the resulting snapshot of the image to other regions and register the AMI from the copied snapshot
#       https://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.register_image
#       https://github.com/smaato/ec2-ami-copy/blob/master/ec2_ami_copy.py
#       https://stackoverflow.com/questions/27004441/how-can-i-transfer-a-ami-from-one-region-to-another-with-non-encrypted-snapsh
#   - better naming for search queries
#   - support for php in beanstalk ( just because. we don't use beanstalk currently )
#   - support for multiple os types, not just amazon linux_linux
#   - port code for conatiner provider; merging into single codebase at a later date
#   -

import argparse
import logging
import datetime
import os
import sys
import time
import jinja2
import boto3
from boto3.session import Session
epoch = time.time()
cwd = os.getcwd()
user = os.getlogin()
aws_owner_id='679593333241'
# aws_owner_id='137112412989'
aws_owner_alias='*'
# aws_owner_alias='amazon'

hvm_beanstalk = 'aws-elasticbeanstalk-amzn-*x86_64*node*hvm*'
hvm_minimal = 'CentOS*7*64*'
# hvm_minimal = 'amzn-ami-minimal-hvm*'
hvm_beanstalk_ecs = 'aws-elasticbeanstalk-amzn-*x86_64-ecs-hvm-*'
hvm_minimal_ecs = 'amzn-ami*.e-amazon-ecs-optimized'
pv_beanstalk = 'aws-elasticbeanstalk-amzn-*x86_64-node*pv*'
pv_minimal = 'amzn-ami-minimal-pv*'
pv_beanstalk_ecs = 'aws-elasticbeanstalk-amzn-*x86_64-ecs-pv-*'
# Image doesn't exist # pv_minimal_ecs = ''
# centos_hvm_minimal ='CentOS 7*'
# centos_owner_id = '675654030569'
# centos_owner_alias = 'aws-marketplace'
# coreos_hvm_stable =
# coreos_pv_stable =
# coreos_hvm_beta =
# coreos_pv_beta =

default_packages = "python27-boto python27-botocore python27-boto3 python27-pip ruby rubygems ruby-libs ruby-irb rubygems facter hiera aws-apitools-common aws-cli sysstat ansible salt-minion telnet"
default_modules = "boto3 botocore awscli futures python-dateutil docutils six jmespath pyasn1 colorama s3transfer rsa urlgrabber urllib3 simplejson setuptools Jinja2 "
epoch = time.time()
extra_script = ""

packer_template = "/var/tmp/packer-"+str(epoch)+".json"
shell_script = "/var/tmp/shell-"+str(epoch)+".sh"
userdata_dest = "/var/tmp/user_data-"+str(epoch)
createuser_dest = "/var/tmp/create_users-"+str(epoch)+".py"
repo_address = "s3.amazonaws.com/local-package-repo" # if not in main VPC, use the local address of xxxx
repo_dns = "s3.amazonaws.com/local-package-repo"
packer_binary = "packer"
curl_binary = "/usr/bin/curl"
ec2_template_path = "templates/ec2/"
scripts_template_path = "templates/scripts/"
local_path = os.path.dirname(os.path.abspath(__file__))
# env = jinja2.Environment(loader=jinja2.FileSystemLoader([local_path+"/templates"]))
secs = 10
elapsed = 0
timeout = 300
timestamp = datetime.datetime.utcnow().isoformat()
ec2_session = Session()
enhanced_networking = ""


shell_script = "/var/tmp/shell-"+str(epoch)+".sh"
createuser_dest = "/var/tmp/create_users-"+str(epoch)+".py"
packer_binary = "~/go-workspace/bin/packer"
curl_binary = "/usr/bin/curl"
packer_template_path = cwd+"/templates/ec2/"
scripts_template_path = cwd+"/templates/scripts/"
os_template_path = cwd+"/templates/os/"
env = jinja2.Environment(loader=jinja2.FileSystemLoader([cwd+"/templates"]))
timestamp = datetime.datetime.utcnow().isoformat()
userdata_source = "user_data.jinja2"
default_packages = [
    "python27-pip",
    "aws-apitools-common",
    "aws-cli",
    "sysstat"
]
default_modules = [
    "boto3",
    "botocore",
    "futures",
    "python-dateutil",
    "docutils",
    "six",
    "jmespath",
    "pyasn1",
    "colorama",
    "s3transfer",
    "rsa",
    "urlgrabber",
    "urllib3",
    "simplejson",
    "setuptools",
    "Jinja2"
]

exclude_list = [
    "ruby",
    "rubygems",
    "ruby-libs",
    "ruby-irb",
    "rubygems",
    "db4*",
    "python27-request",
    "fipscheck*"
]



def check_and_delete_file(filename):
    """ docstring """
    if os.path.isfile(filename) and os.access(filename, os.R_OK):
        logging.info("Found Existing file: %s" % (filename))
        logging.info("Deleting: %s" % (filename))
        os.remove(filename)
    return 0

def find_image(image_name):
    """ docstring """
    images = ec2_client.describe_images(Filters=[{'Name': 'name', 'Values': [image_name]}])
    if len(images['Images']) > 0:
        return images
    else:
        return 100

def delete_image(images):
    """ docstring """
    if len(images) > 0:
        logging.info("Renaming Image before deregistering...")
        logging.info("Deregistering Image %s" % (images['Images'][0]['ImageId']))
        ec2_client.deregister_image(ImageId=images['Images'][0]['ImageId'])
        #
        #  https://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Waiter.ImageExists
        #
        # not working, to implement later
        # waiter = client.get_waiter('image_available')
        # waiter.wait(ImageIds=[images['Images'][0]['ImageId']])
        # logging.info("Image %s is Deregistered " % (images['Images'][0]['ImageId']))
    return 0

def get_ec2_images(ami, owner_id, owner_alias):
      """ docstring """
      images = ec2_client.describe_images(
          Filters=[
              #{'Name': 'root-device-type', 'Values': ['ebs']},
              {'Name': 'name', 'Values': [ami]},
              {'Name': 'owner-alias', 'Values': [owner_alias]},
              {'Name': 'owner-id', 'Values': [owner_id]}

          ]
      )
      image_list = []
      for image in images['Images']:
        #   print image
          image_list.append(image)
          image_list.sort( key=lambda x:datetime.datetime.strptime(x['CreationDate'], '%Y-%m-%dT%H:%M:%S.000Z'))
      image_id = image_list[len(image_list)-1]['ImageId']
      return image_id

def write_packer_template(template_values, template_source, template_dest, virt_type):
    """ docstring """
    check_and_delete_file(template_dest)
    result = ""
    logging.info("[ EXEC  ] - Writing %s Packer Template %s" % (virt_type, template_source))
    packer_env = jinja2.Environment(loader=jinja2.FileSystemLoader([ec2_template_path]))
    template = packer_env.get_template(template_source)
    result = template.render(template_values)
    os.open(template_dest, os.O_CREAT)
    fd = os.open(template_dest, os.O_RDWR)
    os.write(fd, result)
    file_stat = os.stat(template_dest)
    file_size = file_stat.st_size
    logging.info("\tCreated packer template file %s ( %s )" % (template_dest, file_size))
    os.close(fd)
    return 0

def write_shell_template(template_values, template_source, template_dest):
    """ docstring """
    check_and_delete_file(template_dest)
    result = ""
    logging.info("[ EXEC  ] - Writing Shell Template %s" % (template_source))
    packer_env = jinja2.Environment(loader=jinja2.FileSystemLoader([scripts_template_path]))
    template = packer_env.get_template(template_source)
    result = template.render(template_values)
    os.open(template_dest, os.O_CREAT)
    fd = os.open(template_dest, os.O_RDWR)
    os.write(fd, result)
    file_stat = os.stat(template_dest)
    file_size = file_stat.st_size
    logging.info("\tCreated shell file %s ( %s )" % (template_dest, file_size))
    os.close(fd)
    return 0

def write_user_template(template_source, template_dest):
    """ docstring """
    result = ""
    #dest = "/var/tmp/create_users.py"
    check_and_delete_file(template_dest)
    logging.info("[ EXEC  ] - Writing User Template %s" % (template_dest))
    packer_env = jinja2.Environment(loader=jinja2.FileSystemLoader([scripts_template_path]))
    template = packer_env.get_template(template_source)
    result = template.render()
    os.open(template_dest, os.O_CREAT)
    fd = os.open(template_dest, os.O_RDWR)
    os.write(fd, result)
    file_stat = os.stat(template_dest)
    file_size = file_stat.st_size
    logging.info("\tCreated user creation script  %s ( %s )" % (template_dest, file_size))
    os.close(fd)
    return 0

def copy_userdata_file(userdata_template_source, userdata_template_dest):
    """ docstring """
    check_and_delete_file(userdata_template_dest)
    result = ""
    logging.info("[ EXEC  ] - Writing UserData Template %s" % (userdata_template_dest))
    template = env.get_template(userdata_template_source+".jinja2")
    result = template.render()
    os.open(userdata_template_dest, os.O_CREAT)
    fd = os.open(userdata_template_dest, os.O_RDWR)
    os.write(fd, result)
    file_stat = os.stat(userdata_template_dest)
    file_size = file_stat.st_size
    logging.info("\tCreated userdata file %s ( %s )" % (userdata_template_dest, file_size))
    os.close(fd)
    return 0

#def launch_packer(launch_binary, launch_template, sec_group):
def launch_packer(launch_binary, launch_template):
    """ docstring """
    logging.warning("\tLaunching: %s" % (launch_binary))
    logging.warning("\tUsing Template: %s" % (launch_template))
    try:
        os.system(launch_binary + ' build ' + launch_template)
    except:
        logging.info("Packer exception occurred")
        #del_sec_group(sec_group)
    logging.info("Removing Packer template: %s" %(packer_template))
    os.remove(packer_template)
    logging.info("Removing Shell template: %s" % (shell_script))
    os.remove(shell_script)
    logging.info("Removing Userdata template: %s" % (userdata_dest))
    os.remove(userdata_dest)
    logging.info("Removing Createuser template: %s" % (createuser_dest))
    os.remove(createuser_dest)
    return 0

# def copy_snapshot(name):
#     """ docstring """
#     images = client.describe_images(
#         Owners=[account_id],
#         Filters=[
#             {'Name': 'root-device-type', 'Values': ['ebs']},
#             {'Name': 'name', 'Values': [name]}
#         ]
#     )
#     image_list = []
#     for item in images['Images']:
#         image_list.append(item)
#         image_list.sort(key=lambda x: datetime.datetime.strptime(x['CreationDate'], '%Y-%m-%dT%H:%M:%S.000Z'))
#     snap_id = image_list[len(image_list)-1]['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
#     snap_desc = image_list[len(image_list)-1]['Description']
#     logging.info("copying snapshot: %s" % (snap_id))
#     copy_response = client.copy_snapshot(
#         SourceRegion='us-west-2',
#         SourceSnapshotId=snap_id,
#         Description=snap_desc
#     )
#     logging.info("copy_response['SnapshotId']: %s" % (copy_response['SnapshotId']))
#     logging.info("name: %s" % (name))
#     create_ami_from_copy(copy_response['SnapshotId'], name, inst_type)
#     return copy_response['SnapshotId']
#
# def create_ami_from_copy(snapshot_id, name, vtype):
#     """ docstring """
#     logging.info("create image from copy...disabled currently(%s, %s, %s)" % (snapshot_id, name, vtype))
#     # response = client.register_image(
#     #     DryRun=False,
#     #     Name=name,
#     #     Description=name,
#     #     BlockDeviceMappings=[{
#     #         'VirtualName': 'string',
#     #         'DeviceName': 'string',
#     #         'Ebs': {
#     #             'SnapshotId': snapshot_id,
#     #             'VolumeType': 'gp2'
#     #         }
#     #     }],
#     #     VirtualizationType=vtype
#     # )
#     # created_image = client.describe_images(ImageIds=[response[0]])
#     # logging.info("created image id: %s" % (created_image))
#     return 0

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

if __name__ == "__main__":
    # clear = lambda: os.system('clear')
    # clear()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--region',
        nargs='?',
        metavar='',
        help="AWS Region ( Default: us-east-1 )"
    )
    parser.add_argument(
        '--iam_profile',
        nargs='?',
        metavar='',
        default="local-packer-base",
        help="IAM Role ( Default: local-Packer-Base )"
    )
    parser.add_argument(
        '--instance',
        nargs='?',
        metavar='',
        default="t2.micro",
        help="Instance type ( Default: t2.micro )"
    )
    parser.add_argument(
        '--ssh_user',
        nargs='?',
        metavar='',
        default="ec2-user",
        help="EC2 SSH User ( Default: ec2-user )"
    )
    parser.add_argument(
        '--vpc_id',
        nargs='?',
        metavar='',
        help="VPC ID"
    )
    parser.add_argument(
        '--subnet_id',
        nargs='?',
        metavar='',
        help="Subnet ID"
    )
    parser.add_argument(
        '--prefix',
        nargs='?',
        metavar='',
        default="",
        help="AMI Name Prefix ( required )"
    )
    parser.add_argument(
        '--type',
        nargs='?',
        metavar='',
        default="base",
        help="EC2 Host Type [ ec2, beanstalk ] ( Default: ec2 )"
    )
    parser.add_argument(
        '--disk',
        nargs='?',
        metavar='',
        default="base",
        help="EC2 Disk Config[ singledisk, multidisk ] ( Default: singledisk )"
    )
    parser.add_argument(
        '--script',
        nargs='?',
        metavar='',
        default="",
        help="Additional script to execute"
    )
    parser.add_argument(
        '--virt',
        nargs='?',
        metavar='',
        default="hvm",
        help="EC2 Host Virtualization Type"
    )
    parser.add_argument(
        '--user_data_file',
        nargs='?',
        metavar='',
        default="",
        help="UserData File ( Default: NULL )"
    )
    parser.add_argument(
        '--public_cert',
        nargs='?',
        metavar='',
        default="X.509-Packer.crt",
        help="Public X.509 Cert ( Default: X.509-Packer.crt )"
    )
    parser.add_argument(
        '--private_cert',
        nargs='?',
        metavar='',
        default="X.509-Packer.key",
        help="Private X.509 Cert ( Default: X.509-Packer.key )"
    )
    parser.add_argument(
        '--platform',
        nargs='?',
        metavar='',
        default="base",
        help="Platform of the build: node, base, ecs"
    )
    parser.add_argument(
        '-v',
        nargs='?',
        action=VAction,
        dest='verbose'
    )

    args = parser.parse_args()
    if args.verbose == 4:
        logging.basicConfig(level=logging.DEBUG)
        os.environ["PACKER_LOG"] = "debug"
    elif args.verbose == 3:
        logging.basicConfig(level=logging.ERROR)
        os.environ["PACKER_LOG"] = "error"
    elif args.verbose == 2:
        logging.basicConfig(level=logging.WARNING)
        os.environ["PACKER_LOG"] = "warning"
    else:
        logging.basicConfig(level=logging.INFO)
        os.environ["PACKER_LOG"] = "info"

    if not args.prefix:
        logging.info("Image Prefix is required")
        parser.print_help()
        exit(-1)
    if args.user_data_file:
        userdata_source = args.user_data_file
    else:
        userdata_source = "user_data"

    if args.type == "beanstalk":
        exclude_list = "ruby rubygems ruby-libs ruby-irb rubygems db4* python27-request fipscheck* libxml2*"
        if args.virt == "pv":
            enhanced_networking = ''
            inst_type = 'paravirtual'
            if args.platform == "ecs":
                print "******\n\tusing ecs beanstalk pv AMI\n\n"
                default_packages = default_packages+" ecs-init docker"
                ami = pv_beanstalk_ecs
            else:
                print "******\n\tusing default beanstalk pv AMI\n\n"
                ami = pv_beanstalk
        else:
            enhanced_networking = '"enhanced_networking": true,'
            inst_type = 'hvm'
            if args.platform == "ecs":
                print "******\n\tusing ecs beanstalk hvm AMI\n\n"
                default_packages = default_packages+" ecs-init docker"
                ami = hvm_beanstalk_ecs
            else:
                print "******\n\tusing default beanstalk hvm AMI\n\n"
                ami = hvm_beanstalk
    else:
        exclude_list = "ruby rubygems ruby-libs ruby-irb rubygems db4* python27-request fipscheck*"
        if args.virt == "pv":
            enhanced_networking = ''
            inst_type = 'paravirtual'
            if args.platform == "ecs":
                print "No AMI for ECS PV exists. exiting"
                exit(5)
            else:
                print "******\n\tusing default ec2 pv AMI\n\n"
                ami = pv_minimal
        else:
            enhanced_networking = '"enhanced_networking": true,'
            inst_type = 'hvm'
            if args.platform == "ecs":
                print "******\n\tusing ecs ec2 hvm AMI\n\n"
                default_packages = default_packages+" ecs-init docker"
                ami = hvm_minimal_ecs
            else:
                print "******\n\tusing default ec2 hvm AMI\n\n"
                ami = hvm_minimal
    args.prefix = "local_centos-"+args.disk+"-"+args.virt+"_"+args.prefix.replace(" ", "-")+"-"+args.platform.lower()+"-"+args.type
    # local-amzn-<disk>-<virt>_<prefix>-<platform>-<type>
    template_name = args.type+"_"+args.disk
    logging.info("Using origin AMI: %s" % (ami))
    # sg_string = "Temp-Packer-SSH-Ephemeral_"+args.prefix.replace(" ", "-").lower()
    if not args.subnet_id or not args.vpc_id:
        logging.info("\tsubnet_id not defined, looking at metadata of calling host")
        i = os.popen(curl_binary+" -s http://169.254.169.254/latest/dynamic/instance-identity/document |/bin/grep instanceId | awk -F\\\" '{print $4}'")
        instance_id = i.read().rstrip()
    if not args.region:
        logging.info("\tregion not defined, looking at metadata of calling host")
        r = os.popen(curl_binary+" -s http://169.254.169.254/latest/dynamic/instance-identity/document |/bin/grep region | awk -F\\\" '{print $4}'")
        args.region = r.read().rstrip()

    # ec2_session = session.resource('ec2', region_name=args.region)
    logging.info("\tArg Values:")
    logging.info("Using defined value (iam_profile): %s" %(args.iam_profile))
    logging.info("Using defined value (instance): %s" %(args.instance))
    logging.info("Using defined value (ssh_user): %s" %(args.ssh_user))
    logging.info("Using defined value (prefix): %s" %(args.prefix))
    logging.info("Using defined value (type): %s" %(args.type))
    logging.info("Using defined value (disk): %s" %(args.disk))
    logging.info("Using defined value (script): %s" %(args.script))
    logging.info("Using defined value (virt): %s" %(args.virt))
    logging.info("Using defined value (user_data_file): %s" %(args.user_data_file))
    logging.info("Using defined value (public_cert): %s" %(args.public_cert))
    logging.info("Using defined value (private_cert): %s" %(args.private_cert))
    logging.info("Using defined value (platform): %s)" % (args.platform))
    logging.info("Defined Instance Type: %s:" % (inst_type))
    logging.info("Defined Disk: %s:" % (args.disk))
    logging.info("Defined Exclude: %s:" % (exclude_list))
    logging.info("Defined Prefix: %s:" % (args.prefix))
    logging.info("Defined Template Name: %s:" % (template_name))
    ec2_client = boto3.client('ec2', region_name=args.region)
    if not args.subnet_id or not args.vpc_id:
        logging.info("\tsubnet and vpc id's are not defined....retrieving from api")
        instances = ec2_client.describe_instances(
            Filters=[{
                'Name': 'instance-id',
                'Values': [instance_id]
                }]
        )['Reservations']
        for instance in instances:
            args.vpc_id = instance['Instances'][0]['VpcId']
            args.subnet_id = instance['Instances'][0]['NetworkInterfaces'][0]['SubnetId']
            logging.info("Using retrieved value (vpc_id): %s" %(args.vpc_id))
            logging.info("Using retrieved value (subnet_id): %s" %(args.subnet_id))
    else:
        logging.info("Using defined value (vpc): %s " %(args.vpc_id))
        logging.info("Using defined value (subnet): %s" %(args.subnet_id))

    if args.script != "":
        extra_script = '},{\n'
        extra_script = extra_script + '\t"type": "shell",\n'
        extra_script = extra_script + '\t"script": "'+args.script+'",\n'
        extra_script = extra_script + '\t"execute_command": "sudo -E sh \'{{ .Path }}\'"\n'
    else:
        extra_script = ""
    packer_values = {
        'source_ami' : get_ec2_images(ami, aws_owner_id, aws_owner_alias),
        'subnet_id' : args.subnet_id,
        'instance_type': args.instance,
        'instance_profile': args.iam_profile,
        'ssh_user': args.ssh_user,
        'vpc_id': args.vpc_id,
        'prefix': args.prefix,
        'region': args.region,
        'networking': enhanced_networking,
        'scripts': shell_script,
        'template': template_name,
        'packages': default_packages,
        'modules': default_modules,
        'sudo': "{{ .Path }}",
        'timestamp': timestamp,
        'user_data_file': userdata_dest,
        'create_user_script': createuser_dest,
        'extra_script': extra_script
    }
    address = repo_dns
    shell_values = {
        'yumrepo_address': address,
        'exclude_list': exclude_list
    }
    logging.debug("Template Name: %s" % (template_name))
    logging.debug("Packer Values:\n %s" % (packer_values))
    logging.debug("Shell Values:\n %s" % (shell_values))

    if find_image(args.prefix) != 100:
        delete_image(find_image(args.prefix))
        while find_image(args.prefix) != 100:
            status = find_image(args.prefix)
            elapsed = elapsed + secs
            # clear = lambda: os.system('clear')
            # clear()
            sys.stdout.write("Waiting for ami %s to delete ( Elapsed %s secs)" % (args.prefix, elapsed))
            sys.stdout.flush()
            time.sleep(secs)
            if elapsed == timeout:
                logging.info("Timeout %s Reached. Exiting..." % (timeout))
                exit(timeout)

    write_packer_template(packer_values, ec2_template_path+template_name+".jinja2", packer_template, args.virt)
    write_shell_template(shell_values, scripts_template_path+"shell.jinja2", shell_script)
    write_user_template(scripts_template_path+"create_users.jinja2", createuser_dest)
    copy_userdata_file(userdata_source, userdata_dest)
    launch_packer(packer_binary, packer_template)

    # copy_snapshot(args.prefix)
    # del_sec_group(sg_id)
