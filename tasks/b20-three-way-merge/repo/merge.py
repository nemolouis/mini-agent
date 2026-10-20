from collections import namedtuple

MergeResult = namedtuple("MergeResult", "lines conflicts")


def merge3(base, ours, theirs):
    if ours == base:
        return MergeResult(list(theirs), 0)
    if theirs == base or ours == theirs:
        return MergeResult(list(ours), 0)
    lines = ["<<<<<<< ours", *ours, "=======", *theirs, ">>>>>>> theirs"]
    return MergeResult(lines, 1)
