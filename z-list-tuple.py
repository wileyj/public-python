class Solution(object):
    def twoSum(self, nums, target):
        """
        :type nums: List[int]
        :type target: int
        :rtype: List[int]
        """
        print "list_len: %i" % (len(nums))
        for i in xrange(0,len(nums)):
            # print "i: %i" % (nums[i])
            for j in xrange(0,len(nums)):
                if nums[i]+nums[j] == target:
                    print "found 9( %i + %i)" % (nums[i], nums[j])
                    return (nums[i], nums[j], i, j)

        return "no match found"

list = [2, 7, 11, 15]
target = 17
print Solution().twoSum(list,target)
