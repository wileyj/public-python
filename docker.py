#!/usr/bin/env python

#
# sshd on bastion server is tuned badly. hangs until gssapi times out. needs to be fixed

import boto3
from difflib import SequenceMatcher
import argparse
import logging
import sys
import random
import paramiko
import time

region = "us-east-1"
ec2_client = boto3.client('ec2', region_name=region)
ecs_client = boto3.client('ecs', region_name=region)
instance_data = {}
ecs_data = {}

data = {}
hosts = []
total_tasks = 0

def find_instances():
    """ find_instances that are tagged with Application:ECS (assumes only ecs hosts tagged with this) """
    print ""
    logging.debug("************************************************************")
    logging.debug("*** Retrieving instances")
    instances = sorted(
        ec2_client.describe_instances(
            Filters=[{
                'Name': 'vpc-id',
                'Values': ['*']
            },{
                'Name': 'instance-state-name',
                'Values': ['running']
            },{
                'Name': 'tag:Application',
                'Values': ['ECS']
            }]
        )['Reservations'],
        key=lambda x: (
            x['Instances'][0]['LaunchTime'],
            x['Instances'][0]['InstanceId']
        ),
        reverse=True
    )
    logging.debug("\t Total Returned EC2 Instances: %s" % (len(instances)))
    for item in instances:
        t_name = ""
        t_env = ""
        t_vpc = ""
        t_cluster = ""
        t_bu = ""
        t_app = ""
        for tag in item['Instances'][0]['Tags']:
            try:
                if tag['Key'] == "Name":
                    t_name = tag['Value']
                    logging.debug("\tRetrieved Name: %s" % (tag['Value']))
                if tag['Key'] == "Environment":
                    t_env = tag['Value']
                    logging.debug("\tRetrieved Environment: %s" % (tag['Value']))
                if tag['Key'] == "Cluster":
                    t_cluster = tag['Value']
                    logging.debug("\tRetrieved Cluster: %s" % (tag['Value']))
                if tag['Key'] == "BusinessUnit":
                    t_bu = tag['Value']
                    logging.debug("\tRetrieved BusinessUnit: %s" % (tag['Value']))
                if tag['Key'] == "Application":
                    t_app = tag['Value']
                    logging.debug("\tRetrieved Application: %s" % (tag['Value']))
            except:
                pass
        instance_data[item['Instances'][0]['InstanceId']] = {
            'id': item['Instances'][0]['InstanceId'],
            'type': item['Instances'][0]['InstanceType'],
            'private_ip': item['Instances'][0]['PrivateIpAddress'],
            'launch_time': item['Instances'][0]['LaunchTime'],
            'subnet_id': item['Instances'][0]['SubnetId'],
            'name': t_name,
            'vpc': t_vpc,
            'environment': t_env,
            'business_unit': t_bu,
            'cluster': t_cluster,
            'application': t_app
        }
    return True

def find_clusters():
    """ retrieve all data about clusters/containers(tasks) running in each cluster """
    clusters = ecs_client.list_clusters()['clusterArns']
    logging.debug("")
    logging.debug("************************************************************")
    logging.debug("Retrieved %i clusters" % (len(clusters)))
    for cluster in clusters:
        ratio = SequenceMatcher(
            lambda item:
            item == " ",
            "arn:aws:ecs:us-east-1*cluster/default",
            cluster
        ).ratio()
        if ratio < 0.82:
            cluster_short = cluster.split("/")[1]
            if args.cluster and cluster_short != args.cluster:
                continue
            ecs_data[cluster_short] = {}
            logging.debug("Cluster: %s" % (cluster))
            instance_arns = ecs_client.list_container_instances(
                cluster=cluster
            )['containerInstanceArns']
            instances = ecs_client.describe_container_instances(
                cluster=cluster,
                containerInstances=instance_arns
            )['containerInstances']
            logging.debug("Retrieved %i cluster instances" % (len(instances)))
            for instance in instances:
                ecs_data[cluster_short][instance['ec2InstanceId']] = {
                    'instance_id': instance['ec2InstanceId'],
                    'cluster': cluster_short,
                    'containers': []
                }
                logging.debug("\tLooking for tasks in (%s): %s %s" % (instance_data[instance['ec2InstanceId']]['name'], instance_data[instance['ec2InstanceId']]['id'], instance['containerInstanceArn']))
                tasks = ecs_client.list_tasks(
                    cluster=cluster,
                    containerInstance=instance['containerInstanceArn'],
                )['taskArns']
                logging.debug("Retrieved %i cluster tasks" % (len(tasks)))
                for task in tasks:
                    containers = ecs_client.describe_tasks(
                        cluster=cluster,
                        tasks=[task]
                    )['tasks']
                    for container in containers:
                        if args.action != "list":
                            if container['taskDefinitionArn'].split("/")[1].split(":")[0] == args.task:
                                if args.action == "ssh":
                                    if args.random:
                                        hosts.append(instance['ec2InstanceId'])
                                    else:
                                        logging.debug("sshing to %s" % (instance['ec2InstanceId']))
                                        print('*** Initiating Host Interactive Session\n')
                                        interactive().connect(instance_data[instance['ec2InstanceId']]['private_ip'],'')
                                        sys.exit(0)
                                if args.action == "enter":
                                    if args.random:
                                        logging.debug("Recording host %s for random selection" % (instance['ec2InstanceId']))
                                        hosts.append(instance['ec2InstanceId'])
                                    else:
                                        logging.debug("connect to %s -> %s" % (instance['ec2InstanceId'],container['taskDefinitionArn'].split("/")[1].split(":")[0]))
                                        print '*** Initiating Container Interactive Session\n'
                                        interactive().docker_enter(args.user, instance_data[instance['ec2InstanceId']]['private_ip'],args.task)
                                        sys.exit(0)
                                if args.action == "list":
                                    logging.debug("%s matched arg(%s): %s" % (container['taskDefinitionArn'].split("/")[1].split(":")[0], args.action, instance['ec2InstanceId']))
                        ecs_data[cluster_short][instance['ec2InstanceId']]['containers'].append(container['taskDefinitionArn'].split("/")[1].split(":")[0])
                        # logging.info("%s:%s" % (container['taskDefinitionArn'].split("/")[1].split(":")[0], args.task))
    return True

class interactive():
    def connect(self,host, container):
        """Initiate the SSH connection."""
        logging.debug("")
        logging.debug("************************************************************")
        attempts = 3
        count = 0
        while attempts:
            attempts -= 1
            count +=1
            try:
                if attempts > 0:
                    print "Attempting Connection to %s (%i/%i)" % (host, count, attempts)
                    logging.debug("\t connecting to %s@%s" % (args.user, host))
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        host,
                        username=args.user,
                        port=22,
                        allow_agent=True,
                        look_for_keys=True,
                        timeout=5
                    )
                    logging.debug("Connected to %s" % (host))
                    chan = ssh.invoke_shell()
                    # print(repr(ssh.get_transport()))
                    if not container:
                        logging.debug("*** Initiating Interactive Session")
                        interactive().rshell(chan)
                    logging.debug("Closing SSH session to %s" % (host))
                    chan.close()
                    interactive().disconnect()
                    break
                else:
                    print "Max Connection attempts reached (%i/%i)" % (count, attempts)
                    logging.debug("Exiting with code 3")
                    sys.exit(3)
            except paramiko.AuthenticationException:
                print "Authentication failed when connecting to %s" % (host)
                sys.exit(1)
            except:
                print "Connection (%i/%i) failed to  %s, waiting 5s retry" % (count, attempts, host)
                time.sleep(5)

    def disconnect(self):
        """Close the SSH connection."""
        logging.debug("")
        logging.debug("************************************************************")
        try:
            logging.debug("Closing ssh connection to %s" % (self.host))
            self.ssh.close()
        except:
            pass

    def rshell(self, chan):
        """ create interactive ssh shell """
        logging.debug("")
        logging.debug("************************************************************")
        import select
        import termios
        import tty
        import socket
        from paramiko.py3compat import u
        oldtty = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            chan.settimeout(0.0)
            while True:
                r, w, e = select.select([chan, sys.stdin], [], [])
                if chan in r:
                    try:
                        x = u(chan.recv(1024))
                        if len(x) == 0:
                            sys.stdout.write('\n\n')
                            break
                        sys.stdout.write(x)
                        sys.stdout.flush()
                    except socket.timeout:
                        pass
                if sys.stdin in r:
                    x = sys.stdin.read(1)
                    if len(x) == 0:
                        break
                    chan.send(x)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

    def docker_enter(self, user, host, container):
        """ Faking it to connect to a container. relies on ssh and remote /opt/bin/docker-enter existing. this is weak and brittle """
        import os
        logging.debug("")
        logging.debug("************************************************************")
        ssh_host = user+"@"+host
        ssh_timeout = "5"
        ssh_options = "-A -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ConnectTimeout="+ssh_timeout+" -o ConnectionAttempts=1 -tt"
        docker_cmd = "\"/opt/bin/docker-enter "+container+"\" "
        cmd = "ssh "+ssh_options+" "+ssh_host+" "+docker_cmd
        logging.debug("Executing Command: %s" % (cmd))
        returned = os.system(cmd)
        logging.debug("docker_enter func Exiting with code %i" % (returned))
        sys.exit(returned)

class Logging(object):
    # Logging formats
    _log_generic = '%(message)s'
    _log_error_format = '%(asctime)s [%(levelname)s] %(message)s'
    _log_warn_format = '%(asctime)s [%(levelname)s:%(lineno)s] %(message)s'
    _log_debug_format = '%(asctime)s [%(levelname)s] [%(funcName)s:%(lineno)s] %(message)s'

    def configure(self, verbosity = None):
        ''' Configure the logging format and verbosity '''
        # Configure our logging output
        if verbosity:
            verbosity = len(verbosity)+1
        if verbosity >= 4:
            logging.basicConfig(level=logging.DEBUG, format=self._log_debug_format, datefmt='%Y-%m-%d %H:%M:%S')
        elif verbosity >= 3:
            logging.basicConfig(level=logging.WARN, format=self._log_warn_format, datefmt='%Y-%m-%d %H:%M:%S')
        elif verbosity >= 2:
            logging.basicConfig(level=logging.ERROR, format=self._log_error_format, datefmt='%Y-%m-%d %H:%M:%S')
        else:
            logging.basicConfig(level=logging.INFO, format=self._log_generic, datefmt='%Y-%m-%d %H:%M:%S')

        # Configure Boto's logging output
        if verbosity >= 4:
            logging.getLogger('boto').setLevel(logging.CRITICAL)
            logging.getLogger('botocore').setLevel(logging.CRITICAL)
        elif verbosity >= 3:
            logging.getLogger('boto').setLevel(logging.CRITICAL)
            logging.getLogger('botocore').setLevel(logging.CRITICAL)
        else:
            logging.getLogger('boto').setLevel(logging.CRITICAL)
            logging.getLogger('botocore').setLevel(logging.CRITICAL)


if __name__ == "__main__":
    """ init main function """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v',
        dest='verbose',
        nargs='?',
        help="Verbosity"
    )
    parser.add_argument(
        '--random',
        dest='random',
        action='store_true',
        help="Random"
    )
    parser.add_argument(
        '--action',
        choices=[
            "list",
            "ssh",
            "enter",
            "summary"
        ],
        nargs='?',
        metavar='',
        default="list",
        help="Action (list, ssh, enter, summary)",
    )
    parser.add_argument(
        '--task',
        nargs='?',
        metavar='',
        default="",
        help="Container",
    )
    parser.add_argument(
        '--cluster',
        nargs='?',
        metavar='',
        default="",
        help="Cluster Name",
    )
    parser.add_argument(
        '--user',
        nargs='?',
        metavar='',
        default="core",
        help="Instance UserName (default: core)",
    )
    parser.add_argument(
        '--env',
        nargs='?',
        metavar='',
        default="",
        help="Environment of query",
    )
    args = parser.parse_args()
    if args.action != "list" and args.action != "summary" and not args.task:
        print "\t>>> Incorrect Arguments"
        print parser.print_help()
        sys.exit(2)

    Logging().configure(args.verbose)
    __all__ = ('Logging')
    logging = logging.getLogger(__name__)

    logging.debug("")
    logging.debug("*** Defined Args ***")
    logging.debug("\targs.verbose: %s" % (args.verbose))
    logging.debug("\targs.action: %s" % (args.action))
    logging.debug("\targs.task: %s" % (args.task))
    logging.debug("\targs.cluster: %s" % (args.cluster))
    logging.debug("\targs.random: %s" % (args.random))
    logging.debug("\targs.user: %s" % (args.user))
    logging.debug("\targs.envr: %s" % (args.env))
    if args.verbose:
        logging.debug("\tSetting Verbosity Level: %i" % (len(args.verbose)))

    find_instances()
    find_clusters()
    if args.action == "list" or args.action == "summary":
        logging.debug("")
        logging.debug("************************************************************")
        print "Cluster Count: %i" % (len(ecs_data))
        for cluster in ecs_data:
            cluster_tasks = 0
            print "ECS Cluster: %s" % (cluster)
            if args.action == "summary":
                print "  - Total Hosts in cluster: %i" % (len(ecs_data[cluster]))
            for host in ecs_data[cluster]:
                cluster_tasks = len(ecs_data[cluster][host]['containers']) + cluster_tasks
                if args.action == "list":
                    print "    Name:  %s" % (instance_data[ecs_data[cluster][host]['instance_id']]['name'])
                    print "    ID:    %s" % (instance_data[ecs_data[cluster][host]['instance_id']]['id'])
                    print "    IP:    %s" % (instance_data[ecs_data[cluster][host]['instance_id']]['private_ip'])
                    print "    Tasks: %i" % (len(ecs_data[cluster][host]['containers']))
                for i in ecs_data[cluster][host]['containers']:
                    total_tasks += 1
                    if args.action == "list":
                        print "        - %s" % (i)
                if args.action == "list":
                    print ""
            if args.action == "summary":
                print "  - Total Tasks in cluster: %i" % (cluster_tasks)
                cluster_tasks = 0
            print "*************************************************************"
            print ""

    if args.action == "ssh" and args.random:
        logging.debug("Conditional ssh for %s" % (args.action))
        logging.info("Random ssh for %s" % (args.task))
        rand_host = random.choice(hosts)
        print "Selected Random ECS Host: %s"  % (rand_host)
        print "*** Initiating Random Host Interactive Session"
        interactive().connect(instance_data[rand_host]['private_ip'],'')
        logging.debug("Exiting Script with code 0")
        sys.exit(0)


    if total_tasks == 0:
        print "Total Tasks: %i" % (total_tasks)
        logging.info("\tTask %s NOT FOUND" % (args.task))
        logging.debug("Exiting Script with code 3")
        sys.exit(3)
    else:
        print "Total Tasks: %i" % (total_tasks)
        logging.debug("Exiting Script with code 0")
        sys.exit(0)
