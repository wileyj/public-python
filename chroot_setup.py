import sys
import os
from subprocess import Popen, PIPE

jail_root = "/export/jail"
jail_dirs = [
    "/lib64",
    "/usr/share/terminfo",
    "/usr/lib64",
    "/etc",
    "/home/rzshuser/.ssh",
    "/dev",
    "/dev/pts",
    "/jail/proc",
    "/jail/sys"
]
jail_devices = [
    {
        'path': '/dev/null',
        'major': 1,
        'minor': 3
    }, {
        'path': '/dev/random',
        'major': 1,
        'minor': 8
    }, {
        'path': '/dev/tty',
        'major': 1,
        'minor': 8
    }, {
        'path': '/dev/urandom',
        'major': 1,
        'minor': 9
    }
]
system_files = [
    {
        'source': '/lib64/libnss*',
        'dest': '/lib64/'
    }, {
        'source': '/usr/lib64/libnss*',
        'dest': '/usr/lib64/'
    }, {
        'source': '/etc/nsswitch.conf',
        'dest': '/etc/nsswitch.conf'
    }, {
        'source': '/etc/hosts',
        'dest': '/etc/hosts'
    }, {
        'source': '/etc/system-release',
        'dest': '/etc/system-release'
    }, {
        'source': '/etc/security',
        'dest': '/etc/security'
    }, {
        'source': '/usr/share/terminfo/x',
        'dest': '/usr/share/terminfo/'
    }
]
package_list = [
    {
        'binary': '/usr/bin/strace',
        'package': 'strace.x86_64'
    }, {
        'binary': '/usr/bin/host',
        'package': 'bind-utils.x86_64'
    }, {
        'binary': '/bin/ping',
        'package': 'iputils.x86_64'
    }, {
        'binary': '/bin/rzsh',
        'package': 'zsh.x86_64'
    }, {
        'binary': '/bin/traceroute',
        'package': 'traceroute.x86_64'
    }, {
        'binary': '/usr/bin/dig',
        'package': 'bind-utils.x86_64'
    }, {
        'binary': '/usr/bin/nslookup',
        'package': 'bind-utils.x86_64'
    }, {
        'binary': '/usr/bin/ssh',
        'package': 'openssh-clients.x86_64'
    }, {
        'binary': '/usr/bin/telnet',
        'package': 'telnet.x86_64'
    }
]
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
cwd = os.getcwd()
libs = []
print "cwd: %s" % (cwd)


def write_zshenv():
    # /export/jail/etc/zshenv
    file = open("zshenv.txt", "w")
    file.write("""# /etc/zshenv is sourced on all invocations of the
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
    """)
    file.close()
    return True


def write_pam_sshd():
    # /etc/pam.d/sshd
    file = open("pam_sshd.txt", "w")
    file.writelines("""#%PAM-1.0\
auth\trequired\tpam_sepermit.so
auth\tinclude\tpassword-auth
account\trequired\tpam_nologin.so
account\tinclude\tpassword-auth
password\tinclude\tpassword-auth
# pam_selinux.so close should be the first session rule
session\trequired\tpam_selinux.so close
session\trequired\tpam_loginuid.so
# pam_selinux.so open should only be followed by sessions to be executed in the user context
session\trequired\tpam_selinux.so open env_params
session\toptional\tpam_keyinit.so force revoke
session\tinclude\tpassword-auth
session\trequired\tpam_chroot.so
    """)
    file.close()
    return True


def write_fstab():
    return True


def create_dirs(root, dirs):
    return True


def copy_system_files(root, files):
    return True


def mount(source, dest, mount_options):
    return True


def ldd(binary):
    # once we have the libs, we send them to copy_libs
    print "running ldd on %s" % (binary)
    cmd = "/usr/bin/ldd " + binary
    run_cmd(cmd)
    # return the libraries, or else add to a global dict?
    return True


def copy_libs(libs):
    print "copy_libs: %s" % (libs)
    return True


def get_result(p):
    stdout = p.communicate()
    ret = 1
    for s in stdout:
        item = str(s).split("\n")
        print "s: %s" % (s)
        for i in item:
            print "len: %i" % (len(i))
            if len(i) > 4:
                if i.split()[0][0] != "/":
                    print "link: %s (%s)" % (i, i.split(" ")[2])
                    libs.append(i.split(" ")[2])
                else:
                    print "not link: %s (%s)" % (i, i.split(" ")[0])
                    libs.append(i.split(" ")[0])
    return ret


def run_cmd(cmd):
    p = Popen(cmd, shell=True, stdout=PIPE)
    p.wait()
    return get_result(p)


def install_packages(root, package):
    print "root: %s" % (root)
    print "package: %s" % (package)
    # check if binary exists, if not then install file
    # this is faster than querying for each package
    # this is also where we figure out any dependet library for the binaries and copy them over as well
    return True


if __name__ == "__main__":
    if (len(sys.argv) > 1) and (sys.argv[-1] == "-d" or sys.argv[-1] == "--debug"):
        print "** Debug Mode **"
    for item in system_files:
        print "%s => %s" % (item['source'], item['dest'])
    write_pam_sshd()
    write_zshenv()
    for item in package_list:
        run_ldd = 0
        print "binary(%s):: %s" % (item['binary'], item['package'])
        if not os.path.isfile(item['binary']):
            if install_packages(jail_root, item['package']):
                run_ldd = 1
        else:
            run_ldd = 1
        if run_ldd == 1:
            copy_libs(ldd(item['binary']))
