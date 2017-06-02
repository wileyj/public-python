#!/usr/bin/env python


# The MIT License (MIT)
#
# Copyright (c) 2014 Matteo Rinaudo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


### config

# minimum version of Boto that should be installed
min_boto_version = '2.27.0'

# include_aws_us_gov_cloud: variable set to False by default.
include_aws_us_gov_cloud = False

# include_aws_china: variable set to False by default.
include_aws_china = False

### end config


print
print 'Basic Template Builder for AWS VPC'
print '----------------------------------'
print 'Interactively generate basic AWS CloudFormation-based AWS VPC templates.'
print

import json
import re
import sys

try:
    import boto
except ImportError:
    print 'The `boto\' module does not seem to be available, exiting.'
    sys.exit(1)

from distutils.version import StrictVersion
if StrictVersion(boto.__version__) < StrictVersion(min_boto_version):
    print 'Error: the boto package version should be at least: ' + \
        min_boto_version + '; installed: ' + boto.__version__
    sys.exit(1)

# this function validates user input
def get_input_value(
        value_type,
        question_text,
        zero_value_allowed = False,
        empty_value_allowed = False,
        choice_values = [],
        min_value = None,
        max_value = None
):
    value_type = value_type.lower()
    value_type_list = [ 'int', 'str', 'cidr', 'choice' ]
    if value_type not in value_type_list:
        print 'Error: get_input_value(): value_type unknown.'
        sys.exit(1)
    while True:
        input_error = 0
        input_value = raw_input(question_text + ' ')
        try:
            if zero_value_allowed == False \
               and value_type == 'int' \
               and int(input_value) == 0:
                print 'Value cannot be zero.'
                input_error = 1
            # integer value input with minimum set
            elif (value_type == 'int') \
                 and (min_value is not None and max_value is None):
                if int(input_value) < int(min_value):
                    print 'Value cannot be less than ' + str(min_value) + '.'
                    input_error = 1
            # integer value input with maximum set
            elif (value_type == 'int') \
                 and (min_value is None and max_value is not None):
                if int(input_value) > int(max_value):
                    print 'Value cannot be greater than ' + str(max_value) + '.'
                    input_error = 1
            # integer value input with minimum and maximum set
            elif (value_type == 'int') \
                 and (min_value is not None and max_value is not None):
                if int(input_value) < int(min_value):
                    print 'Value cannot be less than ' + str(min_value) + '.'
                    input_error = 1
                elif int(input_value) > int(max_value):
                    print 'Value cannot be greater than ' + str(max_value) + '.'
                    input_error = 1
            elif empty_value_allowed == False \
                 and value_type == 'str' \
                 and str(input_value).strip() == '':
                print 'Value cannot be an empty string.'
                input_error = 1
            elif value_type == 'cidr':
                cidr_pattern = '(^10(\.([0-9]{1,2}|1[0-9]{2}|2[0-4][0-9]|'\
                            '25[0-5])){3}/(1[6-9]|2[0-8])$)|(^172\.(1[6-9]|'\
                            '2[0-9]|3[01])\.([0-9]{1,2}|1[0-9]{2}|2[0-4][0-9]|'\
                            '25[0-5])\.([0-9]{1,2}|1[0-9]{2}|2[0-4][0-9]|'\
                            '25[0-4])/(1[6-9]|2[0-8])$)|'\
                            '(^192\.168\.([0-9]{1,2}|1[0-9]{2}|2[0-4][0-9]|'\
                            '25[0-5])\.([0-9]{1,2}|1[0-9]{2}|2[0-4][0-9]|'\
                            '25[0-4])/(1[6-9]|2[0-8])$)'
                if re.match(cidr_pattern, input_value) == None:
                    print 'CIDR input error; please make sure that:'
                    print '- CIDR block is of the form: n.n.n.n/n'
                    print '- CIDR is a local network IP address block'
                    print '- Subnet value is between /16 and /28.'
                    input_error = 1
            elif value_type == 'choice':
                if not input_value in choice_values:
                    print 'Allowed values: ' + str(choice_values)
                    input_error = 1
            else:
                eval(value_type)(input_value)
        except ValueError:
            print 'Invalid value.'
            input_error = 1
        if input_error == 0:
            break
    return input_value

from boto import ec2
ec2_regions = ec2.regions()
regions = []
for region in ec2_regions:
    regions.append(region.name)

if not include_aws_us_gov_cloud:
    regions = [region for region in regions if region.startswith('us-gov-') == False]
if not include_aws_china:
    regions = [region for region in regions if region.startswith('cn-') == False]

# initialize resources
resources = {}

print 'AWS Regions:'
for r in regions:
    print '  ' + r

# user input: region
print
selected_region = get_input_value(value_type = 'choice', \
            choice_values = regions, \
            question_text = 'In which AWS Region will this template be used?')

# retrieving AZs for the selected region
print
print 'Retrieving Availability Zones for region: ' + selected_region
try:
    ec2_conn = ec2.connect_to_region(selected_region)
except boto.exception.NoAuthHandlerFound:
    print 'Unable to retrieve Availability Zones information.'
    print 'Connection to AWS failed: no credentials found, exiting.'
    sys.exit(1)

all_zones = ec2_conn.get_all_zones()
zones = []
for az in all_zones:
    zones.append(az.name)
    print '  ' + az.name

print
print 'Total Availability Zones in selected region: ' + str(len(zones))

# user input: availability zones
print
total_availability_zones = get_input_value(value_type = 'choice', \
            choice_values = [str(x) for x in range(1, len(all_zones) + 1)], \
            question_text = 'How many Availability Zones?')

# user_input: NAT AMI
print
print 'Retrieving Amazon NAT AMIs for the selected region.'
amazon_nat_ami_list_filters = dict([\
                                ('state', 'available'), ('name', '*-nat-*')])
nat_ami_list = ec2_conn.get_all_images(owners = 'amazon', \
                                        filters = amazon_nat_ami_list_filters)
nat_ami_names = []
s = 1
for a in nat_ami_list:
    if a.owner_alias is not None:
        a_owner_alias = a.owner_alias
    else:
        a_owner_alias = '[n/a]'
    print str(s) + ".\t" + a.id + "\t" + a.ownerId + '/' + a_owner_alias \
        + "\t" + a.name
    nat_ami_names.append(a.name)
    s += 1
print
nat_ami_name_index = get_input_value(value_type = 'choice', \
    choice_values = [str(x) for x in range(1, len(nat_ami_names) + 1)], \
    question_text = 'Amazon NAT AMI to use (specify number on generated list)?')

# generating NAT AMI mappings
ami_items_mapping = {}
amazon_nat_ami_list_filters = dict([\
                    ('state', 'available'), \
                    ('name', nat_ami_names[int(nat_ami_name_index) - 1])])
ami_item_error = False
for region in regions:
    sys.stdout.write('Retrieving Id of the selected AMI from AWS Region ' \
        + region + ': ')
    sys.stdout.flush()
    ec2_conn_tmp = ec2.connect_to_region(region)
    nat_ami_list = ec2_conn_tmp.get_all_images(owners = 'amazon', \
                                        filters = amazon_nat_ami_list_filters)
    try:
        ami_item = str(nat_ami_list[0].id)
        print ami_item
    except IndexError:
        print '[n/a]'
        ami_item = ''
        ami_item_error = True
    ami_mapping_item = dict([(region, dict([('AMI', ami_item)]))])
    ami_items_mapping.update(ami_mapping_item)

if ami_item_error:
    print
    print 'Please note: the selected AMI does not seem to be available'
    print 'on one or more regions, and empty value(s) will be added to'
    print 'each corresponding AMI mapping in the generated template.'
    print 'You might want to press CTRL-c and start over, then try with a '
    print 'different AMI from the list, if available.'
    print 'If you want to use the generated template anyway, please make sure'
    print 'to edit the template and specify valid NAT AMI Id(s).'

# user input: CIDR block
print
vpc_cidrblock = get_input_value(value_type = 'cidr', \
                                question_text = 'CIDR block '\
                                '(format = n.n.n.n/n) for the AWS VPC:')

# user input: public subnets
print
total_public_subnets = get_input_value(value_type = 'int', \
    min_value = total_availability_zones, \
    question_text = 'How many public subnets '\
                                '(min = ' + total_availability_zones + ')?')
public_subnet_cidrs = []
for n in range(1, int(total_public_subnets) + 1):
    public_subnet = get_input_value(value_type = 'cidr', \
                question_text = 'CIDR block for public subnet #' + str(n) + ':')
    public_subnet_cidrs.append(public_subnet)

# bastion host
print
bastion_host_yes_no = get_input_value(value_type = 'choice', \
                            choice_values = ['yes','no'], \
                            question_text = 'Create a Bastion Host (yes/no)?')

if bastion_host_yes_no == 'yes':
    print 'The Bastion Host will be source-locked to a user-specified CIDR.'
    print 'Please specify the TCP connection port to the Bastion Host below.'
    bastion_host_tcp_port = get_input_value(value_type = 'int', \
        min_value = 1, \
        max_value = 65535, \
        question_text = 'TCP port to open on the Bastion Host (e.g. 22, 3389)?')

# user input: private subnets
print
total_private_subnets = get_input_value(value_type = 'int', \
        min_value = 1, \
        question_text = 'How many private subnets (min = 1)?')
private_subnet_cidrs = []
for n in range(1, int(total_private_subnets) + 1):
    private_subnet = get_input_value(value_type = 'cidr', \
            question_text = 'CIDR block for private subnet #' + str(n) + ':')
    private_subnet_cidrs.append(private_subnet)

# user input: template description
print
description = get_input_value(value_type = 'str', \
                              question_text = 'Template description:')

# user input: template filename
print
template_filename = get_input_value(value_type = 'str', \
                                    question_text = 'Template filename:')

# start to build the template
print 'Building template.'

# VPC resource
print 'Describing VPC resource.'
vpc_resource = {'VPC': {\
    'Type': 'AWS::EC2::VPC', \
    'Properties': {\
        'CidrBlock': vpc_cidrblock}}}

# InternetGateway resource
print 'Describing Internet Gateway resource.'
igw_resource = {'InternetGateway': {\
    'Type': 'AWS::EC2::InternetGateway'}}

# VPCGatewayAttachment resource
print 'Describing Internet Gateway Attachment resource.'
igwatt_resource = {'VPCGatewayAttachment': {\
    'DependsOn': 'InternetGateway', \
    'Type': 'AWS::EC2::VPCGatewayAttachment', \
    'Properties': {\
        'VpcId': {'Ref': 'VPC'}, \
        'InternetGatewayId': {'Ref': 'InternetGateway'}}}}

# PublicRouteTable resources
for n in range(1, int(total_availability_zones) + 1):
    public_route_table_resource_name = 'PublicRouteTable' + str(n)
    print 'Describing ' + public_route_table_resource_name + ' resource.'
    public_route_table_resource = {public_route_table_resource_name: {\
        'Type': 'AWS::EC2::RouteTable', \
        'Properties': {\
            'VpcId': {'Ref': 'VPC'}}}}
    resources.update(public_route_table_resource)

# PublicRoute resources
for n in range(1, int(total_availability_zones) + 1):
    public_route_resource_name = 'PublicRoute' + str(n)
    public_route_table_resource_name = 'PublicRouteTable' + str(n)
    print 'Describing ' + public_route_resource_name + ' resource.'
    public_route_resource = {public_route_resource_name: {\
        'Type': 'AWS::EC2::Route', \
        'Properties': {\
            'RouteTableId': {'Ref': public_route_table_resource_name}, \
            'DestinationCidrBlock': '0.0.0.0/0', \
            'GatewayId': {'Ref': 'InternetGateway'}}}}
    resources.update(public_route_resource)

# PublicSubnet resources
for n in range(1, int(total_public_subnets) + 1):
    public_subnet_resource_name = 'PublicSubnet' + str(n)
    print 'Describing ' + public_subnet_resource_name + ' resource.'
    public_subnet_cidr_index = n - 1

    # distribute subnets/AZs evenly
    distribution_modulo = n % (int(total_availability_zones))
    if distribution_modulo == 1 or int(total_availability_zones) == 1:
        subnet_az_suffix = 1
    else:
        subnet_az_suffix = subnet_az_suffix + 1
    subnet_az_resource_name = 'AvailabilityZone' + str(subnet_az_suffix)

    public_subnet_resource = {public_subnet_resource_name: {\
        'Type': 'AWS::EC2::Subnet', \
        'Properties': {\
            'AvailabilityZone': {'Ref': subnet_az_resource_name}, \
            'VpcId': {'Ref': 'VPC'}, \
            'CidrBlock': \
            public_subnet_cidrs[public_subnet_cidr_index]}}}
    resources.update(public_subnet_resource)

# PublicSubnet association to RouteTable resources
route_table_suffix = 1
for n in range(1, int(total_public_subnets) + 1):
    public_subnet_association_resource_name = \
                                    'PublicSubnetRouteTableAssociation' + str(n)
    public_subnet_resource_name = 'PublicSubnet' + str(n)
    print 'Describing ' + public_subnet_association_resource_name + ' resource.'
    public_subnet_cidr_index = n - 1

    # distribute routes/AZs evenly
    distribution_modulo = n % (int(total_availability_zones))
    if distribution_modulo == 1 or int(total_availability_zones) == 1:
        route_table_suffix = 1
    else:
        route_table_suffix = route_table_suffix + 1
    public_route_table_resource_name = \
                                    'PublicRouteTable' + str(route_table_suffix)

    public_subnet_association_resource = \
        {public_subnet_association_resource_name: {\
        'Type': 'AWS::EC2::SubnetRouteTableAssociation', \
        'Properties': {\
            'SubnetId': {'Ref': public_subnet_resource_name}, \
            'RouteTableId' : {'Ref': public_route_table_resource_name}}}}
    resources.update(public_subnet_association_resource)

# PrivateRouteTable resources
for n in range(1, int(total_availability_zones) + 1):
    private_route_table_resource_name = 'PrivateRouteTable' + str(n)
    print 'Describing ' + private_route_table_resource_name + ' resource.'
    private_route_table_resource = {private_route_table_resource_name: {\
        'Type': 'AWS::EC2::RouteTable', \
        'Properties': {\
            'VpcId': {'Ref': 'VPC'}}}}
    resources.update(private_route_table_resource)

# NAT instance resources
for n in range(1, int(total_availability_zones) + 1):
    public_subnet_resource_name = 'PublicSubnet' + str(n)
    nat_instance_resource_name = 'NatInstance' + str(n)
    print 'Describing ' + nat_instance_resource_name + ' resource.'
    nat_instance_resource = {nat_instance_resource_name: {\
        'DependsOn': 'InternetGateway', \
        'Type': 'AWS::EC2::Instance', \
        'Properties': {\
            'Tags': [{'Key': 'Name', 'Value': 'Nat' + str(n)}], \
            'ImageId': {'Fn::FindInMap': ['NatAmi', \
                                    {'Ref': 'AWS::Region'}, 'AMI']},\
            'InstanceType': {'Ref': 'NatInstanceType'}, \
            'KeyName': {'Ref': 'KeyName'}, \
            'SubnetId': {'Ref': public_subnet_resource_name}, \
            'SourceDestCheck': 'false', \
            'SecurityGroupIds': [{'Ref': 'NatSecurityGroup'}]}}}
    resources.update(nat_instance_resource)

# NAT EIP resources
for n in range(1, int(total_availability_zones) + 1):
    nat_eip_resource_name = 'NatEip' + str(n)
    nat_instance_resource_name = 'NatInstance' + str(n)
    print 'Describing ' + nat_eip_resource_name + ' resource.'
    nat_eip_resource = {nat_eip_resource_name: {\
        'DependsOn': 'VPCGatewayAttachment', \
        'Type': 'AWS::EC2::EIP', \
        'Properties': {\
            'Domain': 'vpc', \
            'InstanceId': {'Ref': nat_instance_resource_name}}}}
    resources.update(nat_eip_resource)

# PrivateRoute resources
for n in range(1, int(total_availability_zones) + 1):
    nat_instance_resource_name = 'NatInstance' + str(n)
    private_route_resource_name = 'PrivateRoute' + str(n)
    private_route_table_resource_name = 'PrivateRouteTable' + str(n)
    print 'Describing ' + private_route_resource_name + ' resource.'
    private_route_resource = {private_route_resource_name: {\
        'Type': 'AWS::EC2::Route', \
        'Properties': {\
        'RouteTableId': {'Ref': private_route_table_resource_name}, \
        'DestinationCidrBlock' : '0.0.0.0/0', \
        'InstanceId': {'Ref': nat_instance_resource_name}}}}
    resources.update(private_route_resource)

# PrivateSubnet resources
for n in range(1, int(total_private_subnets) + 1):
    private_subnet_resource_name = 'PrivateSubnet' + str(n)
    print 'Describing ' + private_subnet_resource_name + ' resource.'
    private_subnet_cidr_index = n - 1

    # distribute subnets/AZs evenly
    distribution_modulo = n % (int(total_availability_zones))
    if distribution_modulo == 1 or int(total_availability_zones) == 1:
        subnet_az_suffix = 1
    else:
        subnet_az_suffix = subnet_az_suffix + 1
    subnet_az_resource_name = 'AvailabilityZone' + str(subnet_az_suffix)

    private_subnet_resource = {private_subnet_resource_name: {\
        'Type': 'AWS::EC2::Subnet', \
        'Properties': {\
            'AvailabilityZone': {'Ref': subnet_az_resource_name}, \
            'VpcId': {'Ref': 'VPC'}, \
            'CidrBlock': private_subnet_cidrs[private_subnet_cidr_index]}}}
    resources.update(private_subnet_resource)

# PrivateSubnet association to RouteTable resources
route_table_suffix = 1
for n in range(1, int(total_private_subnets) + 1):
    private_subnet_association_resource_name = \
                                'PrivateSubnetRouteTableAssociation' + str(n)
    private_subnet_resource_name = 'PrivateSubnet' + str(n)
    print 'Describing ' + private_subnet_association_resource_name + \
        ' resource.'
    private_subnet_cidr_index = n - 1

    # distribute routes/AZs evenly
    distribution_modulo = n % (int(total_availability_zones))
    if distribution_modulo == 1 or int(total_availability_zones) == 1:
        route_table_suffix = 1
    else:
        route_table_suffix = route_table_suffix + 1
    private_route_table_resource_name = 'PrivateRouteTable' + \
                                        str(route_table_suffix)

    private_subnet_association_resource = \
        {private_subnet_association_resource_name: {\
        'Type': 'AWS::EC2::SubnetRouteTableAssociation', \
        'Properties': {\
            'SubnetId': {'Ref': private_subnet_resource_name}, \
            'RouteTableId': {'Ref': private_route_table_resource_name}}}}
    resources.update(private_subnet_association_resource)

print 'Describing NatSecurityGroup resource.'
nat_sg_access_from_bastion_host = {}
if bastion_host_yes_no == 'yes':
    nat_sg_access_from_bastion_host = {'IpProtocol': 'tcp', \
            'FromPort': '22', \
            'ToPort': '22', \
            'SourceSecurityGroupId': {'Ref': 'BastionSecurityGroup'}}

nat_security_group_resource = {'NatSecurityGroup': {\
    'Type': 'AWS::EC2::SecurityGroup', \
    'Properties': {\
        'GroupDescription': 'Allow NAT access from the VPC', \
        'VpcId': {'Ref': 'VPC'}, \
        'SecurityGroupIngress': [\
            nat_sg_access_from_bastion_host, \
            {'IpProtocol': 'tcp', 'FromPort': '80', 'ToPort': '80', \
             'CidrIp': vpc_cidrblock}, \
            {'IpProtocol': 'tcp', 'FromPort': '443', 'ToPort': '443', \
             'CidrIp': vpc_cidrblock}], \
        'SecurityGroupEgress': [\
            {'IpProtocol': 'tcp', 'FromPort': '80', 'ToPort': '80', \
             'CidrIp': '0.0.0.0/0'}, \
            {'IpProtocol': 'tcp', 'FromPort': '443', 'ToPort': '443', \
             'CidrIp': '0.0.0.0/0'}]}}}

if bastion_host_yes_no == 'yes':
    # Bastion Security Group
    print 'Describing BastionSecurityGroup resource.'
    bastion_security_group_resource = {'BastionSecurityGroup': {\
        'Type': 'AWS::EC2::SecurityGroup', \
        'Properties': {\
            'GroupDescription': 'Allow remote access from a CIDR range', \
            'VpcId': {'Ref': 'VPC'}, \
            'SecurityGroupIngress': [\
                {'IpProtocol': 'tcp', 'FromPort': {'Ref': 'BastionTcpPort'}, \
                 'ToPort': {'Ref': 'BastionTcpPort'}, \
                 'CidrIp': {'Ref': 'BastionAccessFromCidr'}}], \
            'SecurityGroupEgress': [\
                {'IpProtocol': 'tcp', 'FromPort': '0', 'ToPort': '65535', \
                 'CidrIp': vpc_cidrblock}, \
                {'IpProtocol': 'udp', 'FromPort': '0', 'ToPort': '65535', \
                 'CidrIp': vpc_cidrblock}, \
                {'IpProtocol': 'icmp', 'FromPort': '-1', 'ToPort': '-1', \
                 'CidrIp': vpc_cidrblock}]}}}

    # Bastion Instance
    public_subnet_resource_name = 'PublicSubnet1'
    bastion_instance_resource_name = 'BastionInstance'
    print 'Describing ' + bastion_instance_resource_name + ' resource.'
    bastion_instance_resource = {bastion_instance_resource_name: {\
        'DependsOn': 'InternetGateway', \
        'Type': 'AWS::EC2::Instance', \
        'Properties': {\
            'Tags': [{'Key': 'Name', 'Value': 'BastionHost'}], \
            'ImageId': {'Ref': 'BastionAmi'}, \
            'InstanceType': {'Ref': 'BastionInstanceType'}, \
            'KeyName': {'Ref': 'KeyName'}, \
            'SubnetId': {'Ref': public_subnet_resource_name}, \
            'SecurityGroupIds': [{'Ref': 'BastionSecurityGroup'}]}}}

    # Bastion EIP
    bastion_eip_resource_name = 'BastionEip'
    bastion_instance_resource_name = 'BastionInstance'
    print 'Describing ' + str(bastion_eip_resource_name) + ' resource.'
    bastion_eip_resource = {bastion_eip_resource_name: {\
        'DependsOn': 'VPCGatewayAttachment', \
        'Type': 'AWS::EC2::EIP', \
        'Properties': {\
            'Domain': 'vpc', \
            'InstanceId': {'Ref': bastion_instance_resource_name}}}}

print 'Updating template resources.'
resources.update(vpc_resource)
resources.update(igw_resource)
resources.update(igwatt_resource)
resources.update(public_route_resource)
resources.update(nat_security_group_resource)
if bastion_host_yes_no == 'yes':
    resources.update(bastion_security_group_resource)
    resources.update(bastion_instance_resource)
    resources.update(bastion_eip_resource)

# mappings
print 'Adding template mappings'
mappings = {}

# AMI mapping
print 'Adding AMI mapping.'
ami_mapping = {'NatAmi': ami_items_mapping}

print 'Updating mappings.'
mappings.update(ami_mapping)

# parameters
print 'Adding parameters.'
parameters = {}

for n in range(1, int(total_availability_zones) + 1):
    az_parameter = {'AvailabilityZone' + str(n): {\
        'AllowedPattern': '[-a-zA-Z0-9]*', \
        'ConstraintDescription': 'Alphanumeric characters and dashes only', \
        'Description': 'Availability Zone name', \
        'MaxLength': '15', \
        'MinLength': '10', \
        'Default': zones[n - 1], \
        'Type': 'String'}}
    parameters.update(az_parameter)

key_name_parameter = {'KeyName': {\
    'AllowedPattern': '[-_ a-zA-Z0-9]*', \
    'ConstraintDescription': 'Alphanumeric characters, underscores, '\
                                  'dashes only', \
    'Description': 'Existing key pair to access instances', \
    'MaxLength': '64', \
    'MinLength': '1', \
    'Type': 'String'}}

nat_instance_type_parameter = {'NatInstanceType': {\
    'AllowedValues': [\
        't1.micro', \
        'm1.small', \
        'm1.medium', \
        'm1.large', \
        'm1.xlarge', \
        'm2.xlarge', \
        'm2.2xlarge', \
        'm2.4xlarge', \
        'm3.xlarge', \
        'm3.2xlarge', \
        'c1.medium', \
        'c1.xlarge', \
        'cc1.4xlarge', \
        'cc2.8xlarge', \
        'cg1.4xlarge'],
    'ConstraintDescription': 'Instance type must be of a valid EC2 type', \
    'Default': 'm1.small', \
    'Description': 'EC2 instance type for NAT instances', \
    'Type': 'String'}}

if bastion_host_yes_no == 'yes':
    bastion_access_from_cidr_parameter = {'BastionAccessFromCidr': {\
        'AllowedPattern': '(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/'\
            '(\\d{1,2})', \
        'ConstraintDescription': 'Please specify the CIDR block as n.n.n.n/n', \
        'Default': '0.0.0.0/0', \
        'Description': 'CIDR block allowed to connect to the Bastion Host', \
        'MaxLength': '18', \
        'MinLength': '9', \
        'Type': 'String'}}

    bastion_host_tcp_port_parameter = {'BastionTcpPort': {\
        'AllowedPattern': '[0-9]*', \
        'ConstraintDescription': 'Numbers only', \
        'Default': bastion_host_tcp_port, \
        'Description': 'TCP port the Bastion Host listens to', \
        'Type': 'String'}}

    bastion_ami_parameter = {'BastionAmi': {\
        'Description': 'AMI to use for the Bastion instance', \
        'Type': 'String'}}

    bastion_instance_type_parameter = {'BastionInstanceType': {\
        'AllowedValues': [\
            't1.micro', \
            'm1.small', \
            'm1.medium', \
            'm1.large', \
            'm1.xlarge', \
            'm2.xlarge', \
            'm2.2xlarge', \
            'm2.4xlarge', \
            'm3.xlarge', \
            'm3.2xlarge', \
            'c1.medium', \
            'c1.xlarge', \
            'cc1.4xlarge', \
            'cc2.8xlarge', \
            'cg1.4xlarge'],
        'ConstraintDescription': 'Instance type must be of a valid EC2 type', \
        'Default': 'm1.small', \
        'Description': 'EC2 instance type for the Bastion instance', \
        'Type': 'String'}}

print 'Updating parameters.'
parameters.update(key_name_parameter)
parameters.update(nat_instance_type_parameter)
if bastion_host_yes_no == 'yes':
    parameters.update(bastion_access_from_cidr_parameter)
    parameters.update(bastion_host_tcp_port_parameter)
    parameters.update(bastion_ami_parameter)
    parameters.update(bastion_instance_type_parameter)

# parameters
print 'Adding outputs.'
outputs = {}

# NAT EIPs output
for n in range(1, int(total_availability_zones) + 1):
    nat_eip = {'NatEip' + str(n): {\
        'Description': 'AWS Elastic IP of the NAT instance ' + str(n), \
        'Value': {'Ref': 'NatEip' + str(n)}}}
    outputs.update(nat_eip)

# Bastion EIP output
if bastion_host_yes_no == 'yes':
    bastion_eip = {'BastionEip': {\
        'Description': 'AWS Elastic IP of the Bastion Host', \
        'Value': {'Ref': 'BastionEip'}}}
    outputs.update(bastion_eip)

print 'Assembling template.'
template = {\
    'Description': description, \
    'Parameters': parameters, \
    'Mappings': mappings, \
    'Resources': resources, \
    'Outputs': outputs}

# sorting keys and setting indentation with json.dumps
template = json.dumps(template, sort_keys = True, indent = 2)

# template validation
template_valid = False
from boto import cloudformation
print 'Validating generated template.'
print 'Connecting to the AWS CloudFormation service on region: ' \
    + selected_region
try:
    cfn_conn = cloudformation.connect_to_region(selected_region)
except boto.exception.NoAuthHandlerFound:
    print 'Unable to connect to the AWS CloudFormation service.'
    print 'Connection to AWS failed: no credentials found, exiting.'
    sys.exit(1)
try:
    cfn_conn.validate_template(template_body = template)
    template_valid = True
except boto.exception.BotoServerError, e:
    print 'Template validation failed:'
    print e
    sys.exit(1)

if template_valid:
    print 'Template validation successful.'
    print 'Saving generated template to disk as: ' + template_filename
    f = open(template_filename, 'w')
    f.write(template)
    f.close()
    print 'Done.'
    print
    print 'Template generation is complete.'
    print 'Please make sure to open and review the template before using it,'
    print 'and make changes as you see fit, e.g. security groups, CIDR blocks,'
    print 'and add required resources.'
