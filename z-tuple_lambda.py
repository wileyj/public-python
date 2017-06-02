class Solution:
    def __init__(self, name, grade, age):
        self.name = name
        self.grade = grade
        self.age = age
    def __repr__(self):
        return repr((self.name, self.grade, self.age))

list = [
        Solution('john', 'A', 15),
        Solution('jane', 'B', 12),
        Solution('dave', 'F', 20),
]

this = sorted(
    list,
    key=lambda
    student: student.grade
    # reverse=True

)
print this
