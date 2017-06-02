#!/usr/bin/env python
# python packer_docker.py  --tag ubuntu --image ubuntu:trusty --role base --application ops --repo local/ops --env dev --push
# python packer_docker.py  --tag centos --image centos:7 --application ops --role base --env dev --os centos --template base --repo local/ops --push
# python packer_docker.py  --tag latest --image centos:7 --application ops --role base --env dev --os centos --template base --repo local/ops --push
# python packer_docker.py  --tag latest --image local/ops:base.centos --application ops --role sumologic --env dev --os centos --template base --repo local/ops --push
# python packer_docker.py  --tag latest --image local/ops:base.centos --application shared --role varnish --env dev --os centos --template base --repo local/ops --push
# python packer_docker.py  --tag <tag> --image ubuntu:trusty --application <app name> --role <role name> --repo <repo/name>  --env <stage> --push

import argparse
import logging
import datetime
import os
import time
import jinja2

epoch = time.time()
packer_template = "/var/tmp/packer-"+str(epoch)+".json"
salt_grains_template = "/var/tmp/salt_grains-"+str(epoch)
grains_file = "docker_grains.jinja2"
shell_script = "/var/tmp/shell-"+str(epoch)+".sh"
services_script = "/var/tmp/services-"+str(epoch)+".sh"
packer_binary = "~/go-workspace/bin/packer"
curl_binary = "/usr/bin/curl"
inline = []
packer_template_path = "templates/docker/"
salt_template_path = "templates/salt/"
scripts_template_path = "templates/scripts/"
os_template_path = "templates/userdata/"
# services_template_path = "templates/runit_services/"
cwd = os.getcwd()
env = jinja2.Environment(loader=jinja2.FileSystemLoader([cwd+"/templates"]))
timestamp = datetime.datetime.utcnow().isoformat()
bootstrap_cmd   = "curl -L https://bootstrap.saltstack.com -o bootstrap_salt.sh && sh bootstrap_salt.sh -d -M -N -X && echo 'file_client: local' > /etc/salt/minion"
bootstrap_run   = "salt-call --local  saltutil.sync_grains && salt-call --local  state.highstate"
bootstrap = bootstrap_cmd+" && "+bootstrap_run
salt_state_tree = cwd+"/salt/srv/salt"
salt_pillar_root = cwd+"/salt/srv/pillar"
bootstrap_args = "-d -M -N -X -q -Z -c /tmp"
errors = []
repo_address = "s3.amazonaws.com/local-package-repo" # if not in main VPC, use the local address of xxxx
repo_dns = "s3.amazonaws.com/local-package-repo"
user = os.getlogin()

remove_dirs = [
    "/usr/share/doc",
    "/usr/share/man"
]

default_packages = [
    "curl",
    "python-pip",
    "sudo" # goddamned ubuntu. no sudo installed....really?
]

services_packages = [
    "runit",
    "cronie"
]

default_services = [
    "runit",
    "crond"
]

def check_and_delete_file(filename):
    """ docstring """
    if os.path.isfile(filename) and os.access(filename, os.R_OK):
        logging.error("Found Existing file: %s" % (filename))
        logging.error("Deleting: %s" % (filename))
        os.remove(filename)
    return 0

def write_packer_template(template_values, template_source, template_dest, template_path):
    """ docstring """
    check_and_delete_file(template_dest)
    result = ""
    print "[ EXEC  ] - Writing Template:%s:" % (template_source)
    print "\tLooking for template (%s%s) to write %s" % (template_path, template_source, template_dest)
    jinja2_env = jinja2.Environment(loader=jinja2.FileSystemLoader([template_path]))
    template = jinja2_env.get_template(template_source)
    result = template.render(template_values)
    os.open(template_dest, os.O_CREAT)
    fd = os.open(template_dest, os.O_RDWR)
    os.write(fd, result)
    file_stat = os.stat(template_dest)
    file_size = file_stat.st_size
    print "\tCreated Packer Template: %s ( %s )" % (template_dest, file_size)
    os.close(fd)
    return 0

def write_salt_grains_template(template_values, template_source, template_dest, template_path):
    """ docstring """
    check_and_delete_file(template_dest)
    result = ""
    print "[ EXEC  ] - Writing Salt Template %s" % (template_source)
    print "looking for %s%s to write %s" % (template_path, template_source, template_dest)
    jinja2_env = jinja2.Environment(loader=jinja2.FileSystemLoader([template_path]))
    template = jinja2_env.get_template(template_source)
    result = template.render(template_values)
    os.open(template_dest, os.O_CREAT)
    fd = os.open(template_dest, os.O_RDWR)
    os.write(fd, result)
    file_stat = os.stat(template_dest)
    file_size = file_stat.st_size
    print "\tCreated Salt Grains Template: %s ( %s )" % (template_dest, file_size)
    os.close(fd)
    return 0

def write_shell_template(template_values, template_source, template_dest, template_path):
    """ docstring """
    check_and_delete_file(template_dest)
    result = ""
    print "[ EXEC  ] - Writing Shell Template %s" % (template_source)
    print "looking for %s%s to write %s" % (template_path, template_source, template_dest)
    jinja2_env = jinja2.Environment(loader=jinja2.FileSystemLoader([template_path]))
    template = jinja2_env.get_template(template_source)
    result = template.render(template_values)
    os.open(template_dest, os.O_CREAT)
    fd = os.open(template_dest, os.O_RDWR)
    os.write(fd, result)
    file_stat = os.stat(template_dest)
    file_size = file_stat.st_size
    logging.error("\tCreated Shell Script: %s ( %s )" % (template_dest, file_size))
    os.close(fd)
    return 0

# def write_services_template(template_values, template_source, template_dest, template_path):
#     """ docstring """
#     check_and_delete_file(template_dest)
#     result = ""
#     print "[ EXEC  ] - Writing Services Template %s" % (template_source)
#     print "looking for %s%s to write %s" % (template_path, template_source, template_dest)
#     jinja2_env = jinja2.Environment(loader=jinja2.FileSystemLoader([template_path]))
#     template = jinja2_env.get_template(template_source)
#     result = template.render(template_values)
#     with open(template_dest, 'w') as output:
#         output.write(result)
#         print "\t Adding default_services to %s" % (template_dest)
#         for service in default_services:
#             filename = services_template_path+service+".service"
#             print "\t  Read filename: %s" % (filename)
#             with open(filename, 'r') as f:
#                 for line in f:
#                     output.write(line)
#                 f.closed
#     output.closed
#     file_stat = os.stat(template_dest)
#     file_size = file_stat.st_size
#     print "\tCreated Services Script: %s ( %s )" % (template_dest, file_size)
#     return 0

def launch_packer(launch_binary, launch_template):
    """ docstring """
    logging.warning("\tLaunching: %s" % (launch_binary))
    logging.warning("\tUsing Template: %s" % (launch_template))
    try:
        os.system(launch_binary + ' build ' + launch_template)
    except:
        logging.exception("Packer exception occurred")
    if os.path.isfile(packer_template):
        logging.error("Removing Packer template: %s" %(packer_template))
        os.remove(packer_template)
    if os.path.isfile(shell_script):
        logging.error("Removing Shell template: %s" % (shell_script))
        os.remove(shell_script)
    if os.path.isfile(services_script):
        logging.error("Removing Services template: %s" % (shell_script))
        os.remove(services_script)
    if os.path.isfile(salt_grains_template):
        logging.error("Removing Salt Grains template: %s" % (shell_script))
        os.remove(salt_grains_template)
    return 0

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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--template',
        default="base",
        help="Template to use [default: base]"
    )
    parser.add_argument(
        '--os',
        choices=[
            "centos",
            "ubuntu",
            "debian",
            "amazon",
            "Centos",
            "Ubuntu",
            "Debian",
            "Amazon"
        ],
        default="ubuntu",
        help="OS Type [ ubuntu, centos, amazon, etc ]"
    )
    parser.add_argument(
        '--release',
        default="",
        help="Release of build (currently unused)"
    )
    parser.add_argument(
        '--platform',
        default="",
        help="Platform of the build [ node, php, etc ]"
    )
    parser.add_argument(
        '--script',
        default="",
        nargs='?',
        help="Additional script to execute ( absolute path is required )"
    )
    parser.add_argument(
        '--script-args',
        default="",
        nargs='?',
        help="Additional script args for --script ( surrounded by single quotes )"
    )
    parser.add_argument(
        '--tag',
        default="",
        required=True,
        help="Container Tag [ latest, 0.0.1, etc ] (required)"
    )
    parser.add_argument(
        '--env',
        choices=[
            "dev",
            "development"
            "staging",
            "stage",
            "qa",
            "QA",
            "prod",
            "production"
        ],
        default="dev",
        required=True,
        help="Env of the build [ dev, staging, prod, etc ]"
    )
    parser.add_argument(
        '--application',
        default="",
        required=True,
        help="App to run on container  (required)"
    )
    parser.add_argument(
        '--role',
        default="",
        required=True,
        help="Application Role [ web, redis, etc ]  (required)"
    )
    parser.add_argument(
        '--image',
        default="",
        required=True,
        help="Base Container image to use  (required)"
    )
    parser.add_argument(
        '--repo',
        default="local/base",
        help="Repo of container: eg. name/base"
    )
    parser.add_argument(
        '-v',
        nargs='?',
        action=VAction,
        dest='verbose'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Don't run packer at script conclusion"
    )
    parser.add_argument(
        '--push',
        action='store_true',
        help="Push to dockerhub"
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help="clean all templates from /var/tmp"
    )
    args = parser.parse_args()
    if args.verbose == 4:
        log_format = '%(lineno)-4s %(levelno)-4s %(asctime)-15s  %(message)-4s'
        logging.basicConfig(level=logging.DEBUG, format=log_format)
        os.environ["PACKER_LOG"] = "debug"
    elif args.verbose == 3:
        log_format = '%(lineno)-4s %(levelno)-4s %(message)-4s'
        logging.basicConfig(level=logging.INFO, format=log_format)
        os.environ["PACKER_LOG"] = "info"
    elif args.verbose == 2:
        log_format = '%(lineno)-4s %(levelno)-4s %(message)-4s'
        logging.basicConfig(level=logging.WARNING, format=log_format)
        os.environ["PACKER_LOG"] = "warning"
    else:
        log_format = '%(message)-4s'
        logging.basicConfig(level=logging.ERROR, format=log_format)
        os.environ["PACKER_LOG"] = "error"
    args.prefix_platform = ""
    args.prefix_app = ""
    if args.tag:
        args.tagname = args.tag
        args.tag = args.role+"."+args.tag
    else:
        args.tagname = args.role
        args.tag = args.role
    args.prefix = args.repo+args.prefix_app
    container_name = args.repo+args.prefix_platform+args.prefix_app+args.tag
    template_name = args.template
    if len(args.image.split(":")[0].split("/")) < 2:
        image_name = args.image.split(":")[0].split("/")[0]
        image_repo = image_name
    else:
        image_repo = args.image.split(":")[0].split("/")[0]
        image_name = args.image.split(":")[0].split("/")[1]
    image_tag = args.image.split(":")[1]
    if args.os == "centos" or args.os == "amazon":
        default_packages.append("yum-plugin-priorities salt-minion salt")
    default_services.append(args.role)
    packer_values = {
        'image_name': image_name,
        'image_tag': image_tag,
        'image_repo': image_repo,
        'image': args.image,
        'platform': args.platform,
        'prefix' : args.prefix,
        'tag': args.tag,
        'tagname': args.tagname,
        'release': args.release,
        'os': args.os,
        'application': args.application,
        'role': args.role,
        'environment': args.env,
        'script': shell_script,
        'services_script': services_script,
        'template': template_name,
        'sudo': "{{ .Path }}",
        'timestamp': timestamp,
        'extra_script': args.script,
        'extra_script_args': args.script_args,
        'inline': inline,
        'cwd': cwd,
        'salt_grains_file': salt_grains_template,
        'default_packages': default_packages,
        'services_packages': services_packages,
        'salt_state_tree': salt_state_tree,
        'salt_pillar_root': salt_pillar_root,
        'bootstrap_args': bootstrap_args,
        'docker_push': args.push
    }
    if args.role != 'base':
        args.cleanup = "true"
    else:
        args.cleanup = ""

    salt_grains_values = {
        'tag': args.tag,
        'release': args.release,
        'application': args.application,
        'role': args.role,
        'environment': args.env,
        'cleanup': args.cleanup,
        'type': 'Docker',
        'build_type': 'Packer'
    }

    shell_values = {
        'os': args.os,
        'repo_address':repo_address,
        'repo_dns': repo_dns,
        'image_name': image_name,
        'image_tag': image_tag
    }

    services_values = {
        # 'runit_services': '',
        'services_packages': services_packages
    }

    logging.error("")
    logging.error("Arg Values:")
    logging.error("\tUsing defined value (tag):         %s" %(args.tag))
    logging.error("\tUsing defined value (tagname):     %s" %(args.tagname))
    logging.error("\tUsing defined value (template):    %s" %(args.template))
    logging.error("\tUsing defined value (platform):    %s" %(args.platform))
    logging.error("\tUsing defined value (application): %s" %(args.application))
    logging.error("\tUsing defined value (role):        %s" %(args.role))
    logging.error("\tUsing defined value (env):         %s" %(args.env))
    logging.error("\tUsing defined value (release):     %s" %(args.release))
    logging.error("\tUsing defined value (os):          %s" %(args.os))
    logging.error("\tUsing defined value (verbose):     %s" %(args.verbose))
    logging.error("\tUsing defined value (dry-run):     %s" %(args.dry_run))
    logging.error("\tUsing defined value (script):      %s" %(args.script))
    logging.error("\tUsing defined value (script_args): %s" %(args.script_args))
    logging.error("\tUsing defined value (push):        %s" %(args.push))
    logging.error("")
    logging.error("Prefix Values:")
    logging.error("\tDefined Prefix:                    %s" % (args.prefix))
    logging.error("\tDefined Prefix_platform:           %s" % (args.prefix_platform))
    logging.error("\tDefined Prefix_app:                %s" % (args.prefix_app))
    logging.error("")
    logging.error("Template Values:")
    logging.error("\tDefined Template Name:             %s:" % (template_name))
    logging.error("\tDefined Template image_repo:       %s:" % (image_repo))
    logging.error("\tDefined Template image_name:       %s:" % (image_name))
    logging.error("\tDefined Template image_tag:        %s:" % (image_tag))
    logging.error("")
    logging.error("Jinja Values:")
    logging.error("\tPacker Build Values:")
    for val in packer_values:
        print "\t\t%s: %s" % (val, packer_values[val])
    logging.error("")
    logging.error("\tShell Script Values:")
    for val in shell_values:
        print "\t\t%s: %s" % (val, shell_values[val])
    logging.error("")
    logging.error("\tSalt Grains Values:")
    for val in salt_grains_values:
        print "\t\t%s: %s" % (val, salt_grains_values[val])
    logging.error("")
    logging.error("")
    if args.clean:
        try:
            os.system("rm /var/tmp/*[0-9]*")
        except (IOError, os.error) as why:
            print "Error removing old templates: %s" % (why)
    write_packer_template(packer_values, template_name+".jinja2", packer_template, packer_template_path+args.os+"/")
    write_shell_template(shell_values, args.os+".jinja2", shell_script, os_template_path)
    write_salt_grains_template(salt_grains_values, grains_file, salt_grains_template, salt_template_path)
    if not args.dry_run:
        launch_packer(packer_binary, packer_template)
    exit(0)
