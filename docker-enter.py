# https://boto3.readthedocs.io/en/latest/reference/services/ecs.html#ECS.Client.register_task_definition
import boto3
import argparse
import logging
import re
import random
import sys
import paramiko
import time
import os

os.environ["TERM"] = "vt220"
region = "us-east-1"
ec2_client = boto3.client('ec2', region_name=region)
ecs_client = boto3.client('ecs', region_name=region)
instance_data = {}
ecs_data = {}
total_tasks = 0
data = {}
hosts = []
env_map = {
    "prod": "production",
    "prd": "production",
    "production": "production",
    "staging": "staging",
    "stg": "staging",
    "stg2": "development",
    "dev": "development"
}

def find_instances(cluster, environment):
    """ find_instances that are tagged with Application:ECS (assumes only ecs hosts tagged with this) """
    logger.debug("* Retrieving ASG EC2 Instances")
    host_count = 0
    response = ec2_client.describe_instances(
            Filters=[{
                'Name': 'instance-state-name',
                'Values': ['running']
            },{
                'Name': 'tag:Role',
                'Values': ['ecs']
            },{
                'Name': 'tag:Name',
                'Values': [cluster.lower()]
            },{
                'Name': 'tag:Environment',
                'Values': [environment]
            },{
                'Name': 'tag:Category',
                'Values': ['autoscaling.group']
            }]
        )
    for num, reservation in enumerate(response["Reservations"][0::]):
        for val, instance in enumerate(reservation['Instances'][0::]):
            t_name = ""
            t_env = ""
            t_cluster = ""
            t_bu = ""
            t_app = ""
            logger.debug("EC2 Instance: %s" % (instance['InstanceId']))
            host_count += 1
            for index, tag in enumerate(instance['Tags'][0::]):
                if tag['Key'] == "Name":
                    t_name = tag['Value']
                if tag['Key'] == "Environment":
                    t_env = tag['Value']
                if tag['Key'] == "Cluster":
                    t_cluster = tag['Value']
                if tag['Key'] == "BusinessUnit":
                    t_bu = tag['Value']
                if tag['Key'] == "Application":
                    t_app = tag['Value']
            instance_data[instance['InstanceId']] = {
                'id': instance['InstanceId'],
                'type': instance['InstanceType'],
                'private_ip': instance['PrivateIpAddress'],
                'launch_time': instance['LaunchTime'],
                'subnet_id': instance['SubnetId'],
                'name': t_name,
                'environment': t_env,
                'business_unit': t_bu,
                'cluster': t_cluster,
                'application': t_app
            }
    logger.debug("Discovered %i EC2 Hosts in ECS" % (host_count))
    return host_count

def find_clusters():
    """ retrieve all data about clusters/containers(tasks) running in each cluster """
    logger.debug("* Retrieving ECS Clusters")
    clusters = ecs_client.list_clusters()['clusterArns']
    logger.debug("Retrieved %i clusters" % (len(clusters)-1))
    for num,cluster in enumerate(clusters[0::]):
        if not re.search('default', cluster) and not re.search('SERVICES', cluster):
            cluster_short = cluster.split("/")[1]
            if args.cluster == "*" or args.cluster.upper() == cluster_short:
                ecs_data[cluster_short] = {}
                logger.debug("Cluster: %s" % (cluster_short))
                instance_arns = ecs_client.list_container_instances(
                    cluster=cluster
                )['containerInstanceArns']
                find_cluster_instance(cluster, instance_arns)
    return True

def find_cluster_instance(cluster, instance_arns):
    logger.debug("* Retrieving ECS Cluster Instances (%s)" % (cluster))
    cluster_short = cluster.split("/")[1]
    instances = ecs_client.describe_container_instances(
        cluster=cluster,
        containerInstances=instance_arns
    )['containerInstances']
    if args.random:
        random.shuffle(instances)
    logger.debug("Retrieved %i cluster instances" % (len(instances)))
    logger.debug("  - Retrieving ECS Tasks from EC2 Instances")
    for num,instance in enumerate(instances[0::]):
        try:
            if instance['ec2InstanceId'] in instance_data:
                ecs_data[cluster_short][instance['ec2InstanceId']] = {
                    'instance_id': instance['ec2InstanceId'],
                    'cluster': cluster_short,
                    'containers': []
                }
                logger.debug("\tLooking for tasks in (%s): %s %s" % (instance_data[instance['ec2InstanceId']]['name'], instance_data[instance['ec2InstanceId']]['id'], instance['containerInstanceArn']))
                find_cluster_tasks(cluster, instance)
        except ValueError as e:
            print "Can't find %s in instance_data dict: %s" % (instance['ec2InstanceId'], e)
            pass
    return True

def find_cluster_tasks(cluster, instance):
    cluster_short = cluster.split("/")[1]
    tasks = ecs_client.list_tasks(
        cluster=cluster,
        containerInstance=instance['containerInstanceArn'],
    )['taskArns']
    logger.debug("\t%s:\tRetrieved %i cluster tasks from host(%s)" % (
        cluster_short,
        len(tasks),
        instance_data[instance['ec2InstanceId']]['id']
    ))
    for num, task in enumerate(tasks[0::]):
        containers = ecs_client.describe_tasks(
            cluster=cluster,
            tasks=[tasks[num]]
        )['tasks']
        for val,container in enumerate(containers[0::]):
            logger.debug("\t\t%i %s %s arg(%s) %s" % ( num, instance['ec2InstanceId'], container['taskDefinitionArn'].split("/")[1].split(":")[0], args.action, tasks[num]))
            ecs_data[cluster_short][instance['ec2InstanceId']]['containers'].append(container['taskDefinitionArn'].split("/")[1].split(":")[0])
            if container['taskDefinitionArn'].split("/")[1].split(":")[0] == args.task:
                if args.action == "ssh":
                    logger.debug("sshing to %s" % (instance['ec2InstanceId']))
                    logger.debug("*** Initiating Host Interactive Session\n")
                    interactive().connect(instance_data[instance['ec2InstanceId']]['private_ip'],'')
                    sys.exit(0)
                if args.action == "enter":
                    logger.debug("connect to %s -> %s" % (instance['ec2InstanceId'],container['taskDefinitionArn'].split("/")[1].split(":")[0]))
                    logger.debug("*** Initiating Container Interactive Session\n")
                    interactive().docker_enter(args.user, instance_data[instance['ec2InstanceId']]['private_ip'],args.task)
                    sys.exit(0)
    return True

def ecs_summary(ecs_data):
    task_count = 0
    for cluster in ecs_data:
        if len(ecs_data[cluster]) > 0:
            print "\n%s" % (cluster)
            if args.action == "summary":
                logger.info("\t- Total Hosts in cluster: %i" % (len(ecs_data[cluster])))
            for host in ecs_data[cluster]:
                for task in ecs_data[cluster][host]['containers']:
                    task_count += 1
                    if args.action == "list":
                        print "\t%s\t%s\t%s\t%s" % (
                            instance_data[ecs_data[cluster][host]['instance_id']]['name'],
                            instance_data[ecs_data[cluster][host]['instance_id']]['id'],
                            instance_data[ecs_data[cluster][host]['instance_id']]['private_ip'],
                            task
                        )
            if args.action == "summary":
                logger.info("\t- Total Tasks in cluster: %i" % (task_count))
    return True

class interactive():
    def connect(self,host, container):
        """Initiate the SSH connection."""
        attempts = 3
        count = 0
        while attempts:
            attempts -= 1
            count +=1
            try:
                if attempts > 0:
                    logger.info("Attempting SSH Connection to %s (%i/%i)" % (host, count, attempts))
                    logger.debug("\t connecting to %s@%s" % (args.user, host))
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
                    logger.debug("Connected to %s" % (host))
                    chan = ssh.invoke_shell()
                    if not container:
                        logger.debug("*** Initiating Interactive Session")
                        interactive().rshell(chan)
                    logger.debug("Closing SSH session to %s" % (host))
                    chan.close()
                    interactive().disconnect()
                    break
                else:
                    logger.info("Max Connection attempts reached (%i/%i)" % (count, attempts))
                    logger.debug("Exiting with code 3")
                    sys.exit(3)
            except paramiko.AuthenticationException:
                logger.info("Authentication failed when connecting to %s" % (host))
                sys.exit(1)
            except IOError:
                logger.info("Connection (%i/%i) failed to  %s, waiting 5s retry" % (count, attempts, host))
                time.sleep(5)

    def disconnect(self):
        """Close the SSH connection."""
        logger.debug("")
        try:
            logger.debug("Closing ssh connection")
            self.close()
        except:
            pass


    def rshell(self, chan):
        """ create interactive ssh shell """
        logger.debug("")
        logger.debug("************************************************************")
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
        logger.debug("")
        ssh_host = user+"@"+host
        ssh_timeout = "5"
        ssh_options = "-A -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ConnectTimeout="+ssh_timeout+" -o ConnectionAttempts=1 -tt"
        docker_cmd = "\"/opt/bin/docker-enter "+container+"\" "
        cmd = "ssh "+ssh_options+" "+ssh_host+" "+docker_cmd
        logger.debug("Executing Command: %s" % (cmd))
        returned = os.system(cmd)
        logger.debug("docker_enter func Exiting with code %i" % (returned))
        sys.exit(returned)

class Logging(object):
    # Logging formats
    _log_generic = '%(message)s'
    _log_error_format = '%(asctime)s [%(levelname)s] %(message)s'
    _log_critical_format = '%(asctime)s [%(levelname)s:%(lineno)s] %(message)s'
    _log_debug_format = '%(asctime)s [%(levelname)s] [%(funcName)s:%(lineno)s] %(message)s'

    def configure(self, verbosity = None):
        ''' Configure the logging format and verbosity '''
        # Configure our logging output

        if args.verbose and len(args.verbose)+1 >= 4:
            logging.basicConfig(level=logging.DEBUG)
        elif args.verbose and len(args.verbose)+1 >= 3:
            logging.basicConfig(level=logging.CRITICAL)
        elif args.verbose and len(args.verbose)+1 >= 2:
            logging.basicConfig(level=logging.ERROR)
        else:
            logging.basicConfig(level=logging.INFO, format=self._log_generic, datefmt='%Y-%m-%d %H:%M:%S')
        # Configure Boto's logging output
        if args.verbose and len(args.verbose)+1 >= 4:
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
        '--cluster',
        nargs='?',
        metavar='',
        default="*",
        help="Cluster Name",
    )
    parser.add_argument(
        '--user',
        nargs='?',
        metavar='',
        default="core",
        help="SSH user",
    )
    parser.add_argument(
        '--task',
        nargs='?',
        metavar='',
        default="",
        help="Container",
    )
    parser.add_argument(
        '--env',
        nargs='?',
        metavar='',
        default="*",
        help="Environment of query",
    )
    args = parser.parse_args()
    Logging().configure(args.verbose)
    __all__ = ('Logging')
    logger = logging.getLogger(__name__)
    if args.action != "list" and args.action != "summary" and not args.task:
        print "\t>>> Incorrect Arguments"
        print parser.print_help()
        sys.exit(2)
    if args.env is not "*":
        try:
            args.env = env_map[args.env]
        except KeyError:
            logger.info("Args.env: %s not found in map. defaulting to *" % (args.env))
            args.env = "*"
    logger.debug("")
    logger.debug("*** Defined Args ***")
    logger.debug("\targs.verbose: %s" % (args.verbose))
    logger.debug("\targs.action: %s" % (args.action))
    logger.debug("\targs.task: %s" % (args.task))
    logger.debug("\targs.cluster: %s" % (args.cluster))
    logger.debug("\targs.random: %s" % (args.random))
    logger.debug("\targs.user: %s" % (args.user))
    logger.debug("\targs.env: %s" % (args.env))
    if args.verbose:
        logger.debug("\tSetting Verbosity Level: %i" % (len(args.verbose)))
    if find_instances(args.cluster, args.env) > 0:
        find_clusters()
    else:
        logger.info("[ ERROR ] - zero ec2 instances returned for cluster(%s) in env (%s)" % (args.cluster, args.env))
    if args.action == "list" or args.action == "summary":
        ecs_summary(ecs_data)
