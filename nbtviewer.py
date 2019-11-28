#!/usr/bin/env python3
""" Navigate an NBT file
"""

import nbt


def depth_first_printout(screen, tree, level):
    for branch in tree:

        # Print whatever branch we're currently on, first:
        padding = "  " * level
        name = "unknown"
        value = "unknown"
        size = "unknown"

        if isinstance(branch, nbt.TagType):
            tagtype = str(nbt.TAG_TYPES[branch.TagID].__name__)
            if branch.TagName != None:
                name = branch.TagName
            if not isinstance(branch, (nbt.TAG_End, nbt.TagIterable)):
                value = str(branch.TagPayload)
            if isinstance(branch, nbt.TagIterable):
                value = f"{len(branch.TagPayload)} children"
            size = str(branch.size)
            if isinstance(branch, nbt.TAG_End):
                size = "1"
                value = ""
                name = ""
        else:
            name = str(type(branch))
            value = branch
            if isinstance(branch, str):
                size = str(len(branch))
            
        line = "{:<32} {:>3} {:>5}B {:>16} = {}".format(f"{padding}{tagtype}", level, size, name, value)
        print(line)

        # Then print the branches of the branch:
        if isinstance(branch.TagPayload, list):
            depth_first_printout(screen, branch.TagPayload, level + 1)
            continue


def main():
    # Header
    print("{:<32} {:>3} {:>5}  {:>16} = {}".format(f"TYPE", "LVL", "SIZE", "NAME", "VALUE"))
    print('-' * (32 + 1 + 3 + 1 + 5 + 2 + 16 + 2))

    # Data
    tree = nbt.parse('level.dat.gz')
    depth_first_printout(None, tree, level=0)


if __name__ == "__main__":
    main()
