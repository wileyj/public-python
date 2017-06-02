import operator
import re
a_ips = {}
e_ips = {}
count = 0
for line in open("/Users/wileyj/Downloads/access_log/access_log", 'r'):
    ip = line.split(' ')[0]
    try:
        x = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",ip)
        print x.group()
    except:
        pass
    count = 1
    try:
        if ip in a_ips:
            count = a_ips[ip] + 1
            a_ips[ip] = count
    except:
        pass
    a_ips[ip] = count
this = sorted(
    a_ips.items(),
    key=operator.itemgetter(1),
    reverse=True
)
for i in xrange(0,10):
    print this[i]

for line in open("/Users/wileyj/Downloads/error_log/error_log", 'r'):
    try:
        test = line.split(' ')[7]
        if test == '[client':
            ip = line.split(' ')[8]
            count = 1
            try:
                if ip in e_ips:
                    count = e_ips[ip] + 1
                    e_ips[ip] = count
            except:
                pass
            e_ips[ip] = count
    except:
        pass
that = sorted(
    e_ips.items(),
    key=operator.itemgetter(1),
    reverse=True
)
length = len(that)
print length
if length > 10:
    length = 10
for i in xrange(0,length):
    print that[i]
