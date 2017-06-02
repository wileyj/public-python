import operator
# needs some sample date from apache: access_log

a_ips = {}
e_ips = {}
count = 0
code = 200
# 'path' is the variable string we're searching access_log for
path = "/dccstats/stats-hashes.1week.png"
code_count = 0
path_count = 0
for line in open("./access_log", 'r'):
    ip = line.split(' ')[0]
    tokens = line.split(' ')
    print "tokens len: %i" % (len(tokens))
    for i in range(0,len(tokens)):
        print "\t %s" % (tokens[i])
    if int(tokens[len(tokens)-2]) == code:
        code_count = code_count + 1
    if tokens[len(tokens)-4] == path:
        path_count = path_count + 1
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
print "(%i) code_count: %i" % (code, code_count)
print "(%s) path_count: %i" % (path, path_count)
# length = len(this)
# print length
# if length > 10:
    # length = 10
# for i in xrange(0,length):
    # print this[i]
