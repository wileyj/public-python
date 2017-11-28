import sys
import os
import argparse
import re
import errno
import stat
from shutil import copyfile, copymode
from subprocess import Popen, PIPE
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
cwd = os.getcwd()
libs = {}
jail_root = "/export/jail"
empty_files = [
    "/etc/zprofile.save",
    "/etc/zlogout.save",
    "/etc/zshrc.save",
    "/etc/profile.d/lang.sh.save",
    "/etc/profile.save"
]
dir_list = [
    "/home/rzshuser/.ssh",
    "/dev/pts",
    "/proc",
    "/sys"
]
device_list = [
    {
        'name': '/dev/null',
        'type': stat.S_IFCHR,
        'mode': 0o666,
        'major': 1,
        'minor': 3
    }, {
        'name': '/dev/random',
        'type': stat.S_IFCHR,
        'mode': 0o666,
        'major': 1,
        'minor': 8
    }, {
        'name': '/dev/tty',
        'type': stat.S_IFCHR,
        'mode': 0o666,
        'major': 1,
        'minor': 8
    }, {
        'name': '/dev/urandom',
        'type': stat.S_IFCHR,
        'mode': 0o666,
        'major': 1,
        'minor': 9
    }
]
packages = [
    {
        'binary': '/usr/bin/host',
        'package': 'bind-utils'
    }, {
        'binary': '/bin/ping',
        'package': 'iputils'
    }, {
        'binary': '/bin/rzsh',
        'package': 'zsh'
    }, {
        'binary': '/bin/traceroute',
        'package': 'traceroute'
    }, {
        'binary': '/usr/bin/dig',
        'package': 'bind-utils'
    }, {
        'binary': '/usr/bin/nslookup',
        'package': 'bind-utils'
    }, {
        'binary': '/usr/bin/ssh',
        'package': 'openssh-clients'
    }, {
        'binary': '/usr/bin/telnet',
        'package': 'telnet'
    }
]
print "cwd: %s" % (cwd)


def ldd(binary):
    # once we have the libs, we send them to copy_libs
    cmd = "/usr/bin/ldd " + binary
    print "running command: %s" % (cmd)
    return run_cmd(cmd)


def create_symlink(source, target):
    print "create_symlink Source: %s" % (source)
    print "create_symlink Target: %s" % (target)
    # return True
    try:
        os.symlink(source, target)
        return True
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        pass
    return False


def write_file(filename, content):
    print "Editing File: %s" % (filename)
    file = open(filename, "w")
    file.write(content)
    file.close()
    return True


def create_dir(dir):
    print "Create DIR: %s" % (dir)
    # return True
    try:
        os.makedirs(dir)
        return True
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        pass
    return False


def create_dev(device, dev_type, dev_mode, major, minor):
    print "Create device: %s" % (device)
    print "\tdev type: %s" % (dev_type)
    print "\tdev mode: %i" % (dev_mode)
    print "\t dev major: %i" % (major)
    print "\t dev minor: %i" % (minor)
    try:
        os.mknod(device, dev_type, os.makedev(major, minor))
        os.chmod(device, dev_mode)
        return True
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        pass
    return False


def copy_lib(name, source, target):
    print "copy_lib Name: %s" % (name)
    print "copy_lib Source: %s" % (source)
    print "copy_lib Target: %s" % (target)
    # return True
    try:
        copyfile(source, target)
        copymode(source, target)
        return True
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        pass
    return False


def get_libs(p):
    stdout = p.communicate()
    lib_list = str(stdout[0]).split("\n")[:-1]
    if len(lib_list) > 0:
        for item in lib_list:
            if re.search("linux-vdso.so", item.split(" ")[0]) is None:
                if item.split()[0][0] != "/":
                    source = item.split(" ")[0].strip()
                    target = os.path.realpath(item.split(" ")[2].strip())
                else:
                    source = item.split(" ")[0].strip()
                    target = os.path.realpath(item.split(" ")[0].strip())
                libs[source] = {
                    'name': source,
                    'link': os.path.islink(source),
                    'link_source': os.path.realpath(source),
                    'source': source,
                    'target': target,
                    'base_path_source': os.path.dirname(source),
                    'base_path_target': os.path.dirname(target)
                }
        return True
    else:
        return False


def run_cmd(cmd):
    print "run_cmd; %s" % (cmd)
    p = Popen(cmd, shell=True, stdout=PIPE)
    p.wait()
    return get_libs(p)


def yum_install(package):
    print "Installing package: %s" % (package)
    p = Popen("yum install -y " + package, shell=True, stdout=PIPE)
    return p.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v',
        dest='verbose',
        nargs='?',
        help="Verbosity"
    )
    parser.add_argument(
        '--binary',
        nargs='?',
        metavar='',
        default="",
        help="Binary",
    )
    args = parser.parse_args()
    print "verbose: %s" % (args.verbose)
    print "binary: %s" % (args.binary)
    for item in dir_list:
        if not os.path.exists(jail_root + item):
            if not create_dir(jail_root + item):
                print "Failed to create source dir: %s" % (jail_root + item)
                sys.exit(2)
    for filename in empty_files:
        write_file(filename, "")
    for device in device_list:
        dev_dir = os.path.dirname(jail_root + device['name'])

        print "dev_dir: %s" % (dev_dir)
        if not os.path.exists(dev_dir):
            print "Source Missing: %s" % (dev_dir)
            if not create_dir(dev_dir):
                print "Failed to create source dir: %s" % (dev_dir)
                sys.exit(2)
        create_dev(jail_root + device['name'], device['type'], device['mode'], device['major'], device['minor'])
    if os.path.exists("/export/jail/home/rzshuser/.ssh"):
        if os.path.exists("/export/jail/home/rzshuser/.ssh/known_hosts") and not os.path.islink("/export/jail/home/rzshuser/.ssh/known_hosts"):
            print "rm file /export/jail/home/rzshuser/.ssh/known_hosts"
            # delete_file()
    else:
        print "create dir export/jail/home/rzshuser/.ssh"
    create_symlink("/export/jail/dev/null", "/export/jail/home/rzshuser/.ssh/known_hosts")

    if args.binary:
        ldd(args.binary)
    else:
        for item in packages:
            print "checking if %s exists" % (item['binary'])
            if os.path.exists(item['binary']):
                ldd(item['binary'])
                if not os.path.exists(jail_root + os.path.dirname(item['binary'])):
                    print "Source Missing: %s" % (jail_root + os.path.dirname(item['binary']))
                    if not create_dir(jail_root + os.path.dirname(item['binary'])):
                        print "Failed to create binary dir: %s" % (jail_root + os.path.dirname(item['binary']))
                        sys.exit(1)
                copy_lib(
                    os.path.basename(item['binary']),
                    item['binary'],
                    jail_root + item['binary']
                )
                if re.search("ping", item['binary']):
                    os.chmod(jail_root + item['binary'], 0o04755)
    if len(libs) > 0:
        print "libs len: %i" % (len(libs))
        for lib in libs:
            base_path_source = jail_root + libs[lib]['base_path_source']
            base_path_target = jail_root + libs[lib]['base_path_target']
            print "\nLib:"
            print "\tName: %s" % (libs[lib]['name'])
            print "\tLink: %s" % (libs[lib]['link'])
            print "\tLink_source: %s" % (libs[lib]['link_source'])
            print "\tSource: %s" % (libs[lib]['base_path_source'])
            print "\tTarget: %s" % (libs[lib]['base_path_target'])
            print "\tBase_path_source: %s" % (base_path_source)
            print "\tBase_path_target: %s" % (base_path_target)
            if not os.path.exists(base_path_source):
                print "Source Missing: %s" % (base_path_source)
                if not create_dir(base_path_source):
                    print "Failed to create source dir: %s" % (base_path_source)
                    sys.exit(1)
            if not os.path.exists(base_path_target):
                print "target Missing: %s" % (base_path_target)
                if not create_dir(base_path_target):
                    print "Failed to create target dir: %s" % (base_path_target)
                    sys.exit(1)

            if libs[lib]['link']:
                copy_lib(
                    os.path.basename(libs[lib]['link_source']),
                    os.path.dirname(libs[lib]['source']) + "/" + os.path.basename(libs[lib]['link_source']),
                    jail_root + os.path.dirname(libs[lib]['source']) + "/" + os.path.basename(libs[lib]['link_source'])
                )
                create_symlink(
                    jail_root + os.path.dirname(libs[lib]['source']) + "/" + os.path.basename(libs[lib]['link_source']),
                    base_path_target + "/" + os.path.basename(libs[lib]['name'])
                )
                # disable for now, try to symlink first
                # copy_lib(
                #     os.path.basename(libs[lib]['link_source']),
                #     os.path.dirname(libs[lib]['source']) + "/" + os.path.basename(libs[lib]['link_source']),
                #     base_path_target + "/" + os.path.basename(libs[lib]['name'])
                # )
            else:
                copy_lib(
                    libs[lib]['name'],
                    libs[lib]['base_path_target'] + "/" + libs[lib]['name'],
                    base_path_target + "/" + libs[lib]['name']
                )
    write_file("/etc/sysconfig/chroot_setup", "1")
