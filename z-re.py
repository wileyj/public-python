from operator import itemgetter
import re
class Solution(object):
    def test_email(self, email):
        try:
            x=re.search('(\w+[.|\w])*@(\w+[.])*\w+[.][a-z].*',email)
            return x.group()
        except:
            pass
list = [
    "santa.banta@gmail.co.in",
    "adsf@yahoo",
    "bogusemail123@sillymail.com",
    "santa.banta.manta@gmail.co.in",
    "santa.banta.manta@gmail.co.in.xv.fg.gh",
    "abc.dcf@ghj.org",
    "santa.banta.manta@gmail.co.in.org",
    "zzzzztop@email.com",
]
this = sorted(
    list,
    key=itemgetter(0,1),
    reverse=True
)
for item in this:
    # print item
    if Solution().test_email(item):
        print "%s is valid email" % (item)
    else:
        print "Invalid email: %s" % (item)

string = "atestz"
print string[0]
print string[-1]
print string[0:len(string)-1:]
