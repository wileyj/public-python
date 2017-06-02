class Solution(object):
    def uniq(self, nums):
        newlist = []
        print "newlist: %s" % (newlist)
        print "list_len: %i" % (len(nums))
        for i in xrange(0,len(nums)):
            print "i: %i" % (nums[i])
            numcount = 0
            for j in xrange(0,len(nums)):
                if nums[i] == nums[j]:
                    numcount = numcount+1
            if numcount > 1:
                newlist.append(nums[i])
        print "newlist: %s" % (newlist)
        return newlist

list = [1, 2, 3, 1, 3]
print Solution().uniq(list)
# random val from list
import random
print random.sample(list, 1)[0]
