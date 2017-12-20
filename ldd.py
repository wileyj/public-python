#!/usr/bin/env python
import sys
import os
import argparse
import re
import errno
import stat
import pwd
import grp
# no longer needed since we hardcoded the mount cmd for now
# import ctypes
from shutil import copyfile, copymode
from subprocess import Popen, PIPE
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
cwd = os.getcwd()
libs = {}
fstab_lines = []
jail_root = "/export/jail"
group = "jailed"
user = "rzshuser"
uid = 1501
gid = 1501
homedir = "/home/" + user
chroot_homedir = jail_root + "/home/" + user
sshdir = homedir + "/.ssh"
# keyfile = sshdir + "/authorized_keys"

empty_files = [
    "/etc/zprofile",
    "/etc/zlogout",
    "/etc/zshrc"
]
create_dir_list = [
    homedir,
    sshdir,
    "/lib64",
    "/usr/share/terminfo/x",
    "/usr/lib64",
    "/dev/pts",
    "/proc",
    "/sys",
    "/etc",
    "/etc/security",
    "/tmp"
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
        'fsoptions': 'defaults,hidepid=2',
        'freq': 0,
        'passno': 0
    }, {
        'source': 'sysfs',
        'dest': '/export/jail/sys',
        'fstype': 'sysfs',
        'fsoptions': 'defaults,hidepid=2',
        'freq': 0,
        'passno': 0
    }, {
        'source': 'devpts',
        'dest': '/export/jail/dev/pts',
        'fstype': 'devpts',
        'fsoptions': 'seclabel,gid=5,mode=620,ptmxmode=000',
        'freq': 0,
        'passno': 0
    }, {
        'source': '/dev',
        'dest': '/export/jail/dev',
        'fstype': 'defaults',
        'fsoptions': 'rw,bind',
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
        'binary': '/bin/nc',
        'package': 'nmap-ncat'
    }, {
        'binary': '/sbin/nologin',
        'package': 'util-linux'
    }, {
        'binary': '/bin/ssh-add',
        'package': 'openssh-clients'
    }, {
        'binary': '/bin/ssh-agent',
        'package': 'openssh-clients'
    }, {
        'binary': '/bin/whoami',
        'package': 'coreutils'
    }
]

pam_sshd_lines = [
    "session    required    pam_chroot.so",
    "session    optional    pam_motd.so  motd=/etc/motd"
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


def ldd(binary):
    print "*** Running ldd on %s" % (binary)
    cmd = "/usr/bin/ldd " + binary
    return get_libs(run_cmd(cmd))


def mount(source, target, fs, options=''):
    print "\n*** Mounting (%s -> %s)" % (source, target)
    if source == "/dev" or source == "/sys":
        print "\tfound /dev mount....running this as syscall"
        mount_cmd = "mount --bind " + source + " " + target
        run_cmd(mount_cmd)
    else:
        print "Mounting: %s %s %s %s" % (source, target, fs, options)
        mount_cmd = "mount -t %s %s -o %s %s" % (fs, source, options, target)
        run_cmd(mount_cmd)
        # this isn't working since it can't handle some of the options we need.
        # need to investigate later if it's possible to fix
        # ret = ctypes.CDLL('libc.so.6', use_errno=True).mount(source, target, fs, 4096, options)
        # if ret < 0:
        #     errno = ctypes.get_errno()
        #     raise RuntimeError("Error mounting {} ({}) on {} with options '{}': {}".
        #                        format(source, fs, target, options, os.strerror(errno)))
        #


def create_symlink(source, target):
    print "\n*** Creating SymLink (%s -> %s)" % (source, target)
    # return True
    try:
        os.symlink(source, target)
        return True
    except OSError as exc:
        print "\t - Failed"
        if exc.errno != errno.EEXIST:
            raise
        pass
    return False


def write_file(filename, content):
    print "\n*** Writing File: %s" % (filename)
    file = open(filename, "w")
    file.write(content)
    file.close()
    return True


def create_dir(dir):
    print "\n*** Creating Directory %s" % (dir)
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
    print "\n*** Creating Device %s" % (device)
    print "\t - type: %s" % (dev_type)
    print "\t - mode: %i" % (dev_mode)
    print "\t - major: %i" % (major)
    print "\t - minor: %i" % (minor)
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
    print "\tCopy %s (%s -> %s)" % (name, source, target)
    # return True
    if target == "/export/jail/bin/ssh-agent" and os.path.exists("/export/jail/bin/ssh-agent"):
        print "\t * Matched ssh-agent, but ssh-agent already running. Skipping"
    else:
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
    print "\n*** Removing SUID bits"
    cmd = 'find /export/jail ! -path "*/proc*" -perm -4000 -type f'
    stdout = run_cmd(cmd).communicate()
    suid_list = str(stdout[0]).split("\n")[:-1]
    for item in suid_list:
        print "Remove SUID from: %s" % (item)
        run_cmd("chmod u-s " + item)
    return True


def run_cmd(cmd):
    print "*** Running Command: %s" % (cmd)
    p = Popen(cmd, shell=True, stdout=PIPE)
    p.wait()
    return p


def yum_install(package):
    print "\t Installing Package: %s" % (package)
    p = Popen("yum install -y " + package, shell=True, stdout=PIPE)
    return p.returncode


def check_fstab(lines):
    print "\n*** Checking /etc/fstab"
    f = open(fstab_file, 'r')
    w = open(fstab_file, 'a')
    g = f.readlines()
    f.close()
    for item in lines:
        matched = 0
        token = item.split()
        for line in g:
            if re.search("^" + token[0] + "\s+" + token[1], line) is not None:
                print "Matched: %s" % (token[0])
                matched = 1
                break
        if matched != 1:
            print "Writing line to fstab: %s" % (item)
            w.write(item + "\n")
    w.close()


def check_pamd_sshd(lines):
    print "\n*** Checking file %s" % (pam_sshd_file)
    f = open(pam_sshd_file, 'r')
    w = open(pam_sshd_file, 'a')
    g = f.readlines()
    f.close()
    for item in lines:
        matched = 0
        # print "item: %s" % (item)
        token = item.split()
        # print "\t len: %i" % (len(token))
        # print "token0: %s" % (token[0])
        for line in g:
            # print "line: %s" % (line.strip())
            if re.search("^" + token[0] + "\s+" + token[1] + "\s+" + token[2], line) is not None:
                print "\tMatched: %s" % (line.strip())
                matched = 1
                break
        if matched != 1:
            print "\t  - writing pam.d ssh line: %s" % (item)
            w.write(item + "\n")
    w.close()


def touch(fname, times=None):
    print "\n*** Touching File: %s" % (fname)
    with open(fname, 'a'):
        os.utime(fname, times)


def check_user():
    print "\n*** Checking for user: %s" % (user)
    try:
        print "\t - Found User"
        pwd.getpwnam(user)
    except KeyError:
        print "\t %s Missing" % (user)
        print "\t - Creating user: %s" % (user)
        # create user manually.....lame
        cmd = "useradd -d " + homedir + " -M -N -o -g " + group + " -u " + str(uid) + " -c 'bastion " + user + " account' -s /sbin/nologin " + user
        run_cmd(cmd)
    return True


def check_group():
    print "\n*** Checking group: %s" % (group)
    try:
        print "\tFound group"
        grp.getgrnam(group)
        pass
    except KeyError:
        print "\t %s Missing" % (group)
        print "\t  - Creating group: %s" % (group)
        # create group manually.....lame
        cmd = "groupadd -g " + gid + " " + group
        run_cmd(cmd)
    return True


def check_rzshuser_files():
    check_user()
    check_group()
    print "\n*** Checking user(%s) files" % (user)
    if not os.path.exists(homedir):
        print "\tHomedir Missing"
        print "\t  - Creating user homedir " + homedir
        if not create_dir(homedir):
            print "\t    - Failed to create user homedir: %s" % (homedir)
    # if not os.path.exists(sshdir):
    #     print " - Creating user sshdir " + sshdir
    #     if not create_dir(sshdir):
    #         print "Failed to create user sshdir: %s" % (sshdir)
    # if not os.path.exists(keyfile):
    #     print "Creating user authorized_keys file " + keyfile
    #     touch(keyfile)

    # check file perms
    st = os.stat(homedir)
    if oct(st.st_mode)[-3:] is not 750:
        print "\t - Setting %s perm to %s" % (homedir, "0o770")
        os.chmod(homedir, 0o770)
        os.chown(homedir, uid, gid)
    # else:
    #     print "homedir perm: %s" % (oct(st.st_mode)[-3:])
    # st = os.stat(sshdir)
    # if oct(st.st_mode)[-3:] is not 700:
    #     print "setting %s perm to %s" % (sshdir, "0o700")
    #     os.chmod(sshdir, 0o700)
    #     os.chown(sshdir, uid, gid)
    # else:
    #     print "sshdir perm: %s" % (oct(st.st_mode)[-3:])
    # st = os.stat(keyfile)
    # if oct(st.st_mode)[-3:] is not 640:
    #     print "setting %s perm to %s" % (keyfile, "0o640")
    #     os.chmod(keyfile, 0o640)
    #     os.chown(keyfile, uid, gid)
    # else:
    #     print "keyfile perm: %s" % (oct(st.st_mode)[-3:])
    if os.path.exists(chroot_homedir):
        print "Found existing jail homedir: %s" % (chroot_homedir)
        st = os.stat(chroot_homedir)
        if oct(st.st_mode)[-3:] is not 770:
            print "  chmod 770 on %s" % (chroot_homedir)
            os.chmod(chroot_homedir, 0o770)
        print "  chown %i %i on %s" % (uid, gid, chroot_homedir)
        os.chown(chroot_homedir, uid, gid)
    return True


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
    for item in create_dir_list:
        if not os.path.exists(jail_root + item):
            if not create_dir(jail_root + item):
                print "Exiting. Failed to create source dir: %s" % (jail_root + item)
                sys.exit(2)
        if item is "/tmp":
            print "Found tmp dir: %s" % (item)
            run_cmd("chmod a+w " + jail_root + item)
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
            print "Missing Destination path: %s" % (item['dest'])
    for fsmount in mounts:
        if not os.path.ismount(fsmount['dest']):
            print "\t - %s is not mounted: %s" % (mount, fsmount['dest'])
            mount(fsmount['source'], fsmount['dest'], fsmount['fstype'], fsmount['fsoptions'])
        fstab_lines.append(fsmount['source'] + "\t" + fsmount['dest'] + "\t" + fsmount['fstype'] + "\t" + fsmount['fsoptions'] + "\t0 0")
    for device in device_list:
        dev_dir = os.path.dirname(jail_root + device['name'])
        if not os.path.exists(dev_dir):
            print "Source Missing: %s" % (dev_dir)
            if not create_dir(dev_dir):
                print "Failed to create source dir: %s" % (dev_dir)
                sys.exit(2)
        create_dev(jail_root + device['name'], device['type'], device['mode'], device['major'], device['minor'])
    if os.path.exists("/export/jail" + sshdir):
        if os.path.exists("/export/jail" + sshdir + "/known_hosts") and not os.path.islink("/export/jail" + sshdir + "/known_hosts"):
            print "Found %s....Removingit" % ("/export/jail/" + sshdir + "/known_hosts")
            os.remove("/export/jail/" + sshdir + "/known_hosts")
            create_symlink("/export/jail/dev/null", "/export/jail" + sshdir + "/known_hosts")
    else:
        create_symlink("/export/jail/dev/null", "/export/jail" + sshdir + "/known_hosts")
    if args.binary:
        ldd(args.binary)
    else:
        print "*** Checking on Packages/Binaries"
        for item in packages:
            print "Checking if %s exists" % (item['binary'])
            file_name = os.path.basename(item['binary'])
            file_source = item['binary']
            file_target = jail_root + item['binary']
            if file_name == "zsh":
                file_target = file_target.replace("zsh", "rzsh")
            if not os.path.exists(file_source):
                print "Installing Package: %s" % (item['package'])
                run_cmd("yum install -y " + item['package'])
            if os.path.exists(file_source) and not os.path.exists(file_target):
                ldd(item['binary'])
                if not os.path.exists(jail_root + os.path.dirname(item['binary'])):
                    print "Source Missing: %s" % (jail_root + os.path.dirname(item['binary']))
                    if not create_dir(jail_root + os.path.dirname(item['binary'])):
                        print "Failed to create binary dir: %s" % (jail_root + os.path.dirname(item['binary']))
                        sys.exit(1)

                copy_lib(
                    file_name,
                    file_source,
                    file_target
                )
                if re.search("ping", item['binary']):
                    os.chmod(jail_root + item['binary'], 0o04755)
    if len(libs) > 0:
        print "*** Total Number of libraries to copy: %i" % (len(libs))
        for lib in libs:
            base_path_source = jail_root + libs[lib]['base_path_source']
            base_path_target = jail_root + libs[lib]['base_path_target']
            if not os.path.exists(base_path_source):
                print "- Source  Missing: %s" % (base_path_source)
                if not create_dir(base_path_source):
                    print "Failed to create source dir: %s" % (base_path_source)
                    sys.exit(1)
            if not os.path.exists(base_path_target):
                print "- Target  Missing: %s" % (base_path_target)
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
        content = ""
        write_file(jail_root + filename, content)
    write_file(jail_root + zshenv_file, zshenv)
    check_pamd_sshd(pam_sshd_lines)
    check_rzshuser_files()
    if (len(fstab_lines) > 0):
        check_fstab(fstab_lines)
        run_cmd("mount -a")
        # need a check around this command: it'll fail if run more than once
        if not os.path.exists("/export/jail/tmp/ssh-agent"):
            run_cmd("/export/jail/bin/ssh-agent -a /export/jail/tmp/ssh-agent")
    write_file("/etc/sysconfig/chroot_setup", "1")
