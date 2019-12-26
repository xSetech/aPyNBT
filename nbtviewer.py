#!/usr/bin/env python3
""" Navigate an NBT file
"""

import sys

import nbt


def depth_first_printout(screen, tree, level):
    for branch in tree:

        # Print whatever branch we're currently on, first:
        padding = "  " * level
        name = "unknown"
        value = "unknown"
        size = "unknown"
        tagtype = "unknown"

        if isinstance(branch, nbt.Tag):
            tagtype = str(nbt.TAG_TYPES[branch.tid].__name__)
            if branch.name != None:
                name = branch.name

            # scalar values the payload's repr
            if not isinstance(branch, (nbt.TAG_End, nbt.TagIterable)):
                value = str(branch.payload)

            # iterables list the number of elements stored
            if isinstance(branch, nbt.TagIterable):
                value = f"{len(branch.payload)} children"
                if isinstance(branch, nbt.TAG_List):
                    value += f" of type {nbt.TAG_TYPES[branch.tagID].__name__}"

            # size
            size = str(branch._size)

            if isinstance(branch, nbt.TAG_End):
                size = "1"
                value = ""
                name = ""
        else:
            tagtype = str(type(branch))
            name = str(type(branch))
            value = branch
            if isinstance(branch, str):
                size = str(len(branch))
            
        line = "{:<32} {:>3} {:>5}B {:>24} = {}".format(f"{padding}{tagtype}", level, size, name, value)
        print(line)

        # Then print the branches of the branch:
        if isinstance(branch, nbt.Tag) and hasattr(branch.payload, "__iter__"):
            if not isinstance(branch.payload, (str,)):
                depth_first_printout(screen, branch.payload, level + 1)


def main():
    # Header
    print("{:<32} {:>3} {:>5}  {:>24} = {}".format(f"TYPE", "LVL", "SIZE", "NAME", "VALUE"))
    print('-' * (32 + 1 + 3 + 1 + 5 + 2 + 24 + 2))

    # Data
    tree = nbt.deserialize_file(sys.argv[1])
    depth_first_printout(None, tree, level=0)


if __name__ == "__main__":
    main()
