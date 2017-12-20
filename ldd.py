import sys
import os
import argparse
import re
import errno
import stat
import ctypes
from shutil import copyfile, copymode
from subprocess import Popen, PIPE
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
cwd = os.getcwd()
libs = {}
fstab_lines = []
jail_root = "/export/jail"
empty_files = [
    "/etc/zprofile",
    "/etc/zlogout",
    "/etc/zshrc"
]
create_dir_list = [
    "/home/rzshuser/.ssh",
    "/lib64",
    "/usr/share/terminfo/x",
    "/usr/lib64",
    "/dev/pts",
    "/proc",
    "/sys",
    "/etc",
    "/etc/security"
]
copy_file_list = [
    "/etc/nsswitch.conf",
    "/etc/hosts",
    "/etc/passwd",
    "/etc/group",
    "/etc/resolv.conf",
    "/etc/system-release"
]
copy_dir_list = [
    {
        "source": "/lib64/libnss*",
        "dest": jail_root + "/lib64/"
    }, {
        "source": "/usr/lib64/libnss*",
        "dest": jail_root + "/usr/lib64/"
    }, {
        "source": "/etc/security/*",
        "dest": jail_root + "/etc/security/"
    }, {
        "source": "/usr/share/terminfo/x/*",
        "dest": jail_root + "/usr/share/terminfo/x/"
    }, {
        "source": "/usr/lib64/zsh",
        "dest": jail_root + "/usr/lib64/"
    }, {
        "source": "/usr/lib64/ld-linux*",
        "dest": jail_root + "/lib64/"
    }
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
mounts = [
    {
        'source': 'proc',
        'dest': '/export/jail/proc',
        'fstype': 'proc',
        'fsoptions': '',
        'freq': 0,
        'passno': 0
    }, {
        'source': 'sysfs',
        'dest': '/export/jail/sys',
        'fstype': 'sysfs',
        'fsoptions': '',
        'freq': 0,
        'passno': 0
    }, {
        'source': 'devpts',
        'dest': '/export/jail/dev/pts',
        'fstype': 'devpts',
        'fsoptions': 'seclabel,gid=5,mode=620,ptmxmode=000',
        'freq': 0,
        'passno': 0
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
        'binary': '/bin/zsh',
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
pam_sshd_lines = [
    "session    required    pam_chroot.so"
]
pam_sshd_file = "/etc/pam.d/sshd"
fstab_file = "/etc/fstab"
zshenv_file = "/etc/zshenv"

zshenv = """
#
# /etc/zshenv is sourced on all invocations of the
# shell, unless the -f option is set.  It should
# contain commands to set the command search path,
# plus other important environment variables.
# .zshenv should not contain commands that produce
# output or assume the shell is attached to a tty.
#

export PATH=/usr/bin:/bin
alias bindkey=""
alias compcall=""
alias compctl=""
alias compsys=""
alias source=""
alias vared=""
alias zle=""
alias bg=""

disable compgroups
disable compquote
disable comptags
disable comptry
disable compvalues
disable pwd
disable alias
disable autoload
disable break
disable builtin
disable command
disable comparguments
disable compcall
disable compctl
disable compdescribe
disable continue
disable declare
disable dirs
disable disown
disable echo
disable echotc
disable echoti
disable emulate
disable enable
disable eval
disable exec
disable export
disable false
disable float
disable functions
disable getln
disable getopts
disable hash
disable integer
disable let
disable limit
disable local
disable log
disable noglob
disable popd
disable print
disable pushd
disable pushln
disable read
disable readonly
disable rehash
disable sched
disable set
disable setopt
disable shift
disable source
disable suspend
disable test
disable times
disable trap
disable true
disable ttyctl
disable type
disable typeset
disable ulimit
disable umask
disable unalias
disable unfunction
disable unhash
disable unlimit
disable unset
disable unsetopt
disable vared
disable whence
disable where
disable which
disable zcompile
disable zformat
disable zle
disable zmodload
disable zparseopts
disable zregexparse
disable zstyle
"""
print "cwd: %s" % (cwd)


def ldd(binary):
    cmd = "/usr/bin/ldd " + binary
    print "running command: %s" % (cmd)
    return get_libs(run_cmd(cmd))


def mount(source, target, fs, options=''):
    ret = ctypes.CDLL('libc.so.6', use_errno=True).mount(source, target, fs, 0, options)
    if ret < 0:
        errno = ctypes.get_errno()
        raise RuntimeError("Error mounting {} ({}) on {} with options '{}': {}".
                           format(source, fs, target, options, os.strerror(errno)))


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


def remove_suid():
    cmd = 'find /export/jail ! -path "*/proc*" -perm -4000 -type f'
    stdout = run_cmd(cmd).communicate()
    suid_list = str(stdout[0]).split("\n")[:-1]
    for item in suid_list:
        print "Line: %s" % (item)
        # chmod u-s item
    return True


def run_cmd(cmd):
    print "runing command: %s" % (cmd)
    p = Popen(cmd, shell=True, stdout=PIPE)
    p.wait()
    return p


def yum_install(package):
    print "Installing package: %s" % (package)
    p = Popen("yum install -y " + package, shell=True, stdout=PIPE)
    return p.returncode


def check_fstab(lines):
    f = open(fstab_file, 'r')
    w = open(fstab_file, 'a')
    g = f.readlines()
    f.close()
    for item in lines:
        matched = 0
        print "item: %s" % (item)
        token = item.split()
        for line in g:
            if re.search("^" + token[0] + "\s+" + token[1], line) is not None:
                print "Matched: %s" % (token[0])
                matched = 1
                break
        if matched != 1:
            w.write(item + "\n")
    w.close()


def check_pamd_sshd(lines):
    f = open(pam_sshd_file, 'r')
    w = open(pam_sshd_file, 'a')
    g = f.readlines()
    f.close()
    for item in lines:
        matched = 0
        print "item: %s" % (item)
        token = item.split()
        print "\t len: %i" % (len(token))
        print "token0: %s" % (token[0])
        for line in g:
            print "line: %s" % (line.strip())
            if re.search("^" + token[0] + "\s+" + token[1] + "\s+" + token[2], line) is not None:
                print "Matched: %s" % (line)
                matched = 1
                break
        if matched != 1:
            print "write item to %s: %s" % (pam_sshd_file, item)
            w.write(item + "\n")
    w.close()


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
    for item in create_dir_list:
        if not os.path.exists(jail_root + item):
            if not create_dir(jail_root + item):
                print "Failed to create source dir: %s" % (jail_root + item)
                sys.exit(2)
    for item in copy_file_list:
        if not os.path.exists(jail_root + item):
            copy_lib(
                os.path.basename(item),
                item,
                jail_root + item
            )
    for item in copy_dir_list:
        if os.path.exists(item['dest']):
            run_cmd("cp -a " + item['source'] + " " + item['dest'])
        else:
            print "MISSING path: %s" % (item['dest'])
    for fsmount in mounts:
        if not os.path.ismount(fsmount['dest']):
            print "mount: %s" % (fsmount['source'])
            mount(fsmount['source'], fsmount['dest'], fsmount['fstype'], fsmount['fsoptions'])
            fstab_lines.append(fsmount['source'] + "\t" + fsmount['dest'] + "\t" + fsmount['fstype'] + "\t" + fsmount['fsoptions'] + "\t0 0")
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
            print "\nchecking if %s exists" % (item['binary'])
            if not os.path.exists(item['binary']):
                print "Installing package: %s" % (item['package'])
                run_cmd("yum install -y " + item['package'])
            if os.path.exists(item['binary']):
                ldd(item['binary'])
                if not os.path.exists(jail_root + os.path.dirname(item['binary'])):
                    print "Source Missing: %s" % (jail_root + os.path.dirname(item['binary']))
                    if not create_dir(jail_root + os.path.dirname(item['binary'])):
                        print "Failed to create binary dir: %s" % (jail_root + os.path.dirname(item['binary']))
                        sys.exit(1)
                file_name = os.path.basename(item['binary'])
                file_source = item['binary']
                file_target = jail_root + item['binary']
                if file_name == "zsh":
                    file_target = file_target.replace("zsh", "rzsh")
                print "file_name: %s" % (file_name)
                print "file_source: %s" % (file_source)
                print "file_target: %s" % (file_target)
                copy_lib(
                    file_name,
                    file_source,
                    file_target
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
            else:
                copy_lib(
                    libs[lib]['name'],
                    libs[lib]['base_path_target'] + "/" + libs[lib]['name'],
                    base_path_target + "/" + libs[lib]['name']
                )
    remove_suid()
    for filename in empty_files:
        write_file(jail_root + filename, "")
    write_file(jail_root + zshenv_file, zshenv)
    check_pamd_sshd(pam_sshd_lines)
    if (len(fstab_lines) > 0):
        check_fstab(fstab_lines)
        run_cmd("mount -a")
    write_file("/etc/sysconfig/chroot_setup", "1")
