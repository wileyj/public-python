import operator
x = {
    1: 'd) one',
    2: 'e) two',
    3: 'a) three',
    4: 'c) four',
    5: 'b) five'
}
sorted_x = sorted(
    x.items(),
    key=operator.itemgetter(1),
    # reverse=True
)
print sorted_x
