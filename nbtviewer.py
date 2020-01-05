#!/usr/bin/env python3
""" Navigate an NBT file
"""

import sys

import aPyNBT.nbt as nbt
import aPyNBT.region as region

line_template = "{:<32} {:>3} {:>5}B {:>24} = {}"
max_values_per_line = 16


def print_nbt(tree, level: int = 0, parent: nbt.Tag = None):
    padding = "  " * level

    name = "unknown"
    value = "unknown"
    size = "unknown"
    tagtype = "unknown"

    # If the parent tag type is expected to store a huge number of primitives,
    # then print multiple elements per line.
    multi_values_per_line = isinstance(parent, (nbt.TAG_Byte_Array, nbt.TAG_Int_Array, nbt.TAG_Long_Array))
    values = None

    if multi_values_per_line:
        name = ""
        size = ""

    for branch in tree:

        if isinstance(branch, nbt.Tag):

            size = str(branch._size)
            tagtype = str(nbt.TAG_TYPES[branch.tid].__name__)

            # name
            if branch.name is not None:
                name = branch.name
            elif isinstance(parent, nbt.TAG_List):
                name = ""  # TAG_List stores unnamed tags

            # value (typically the payload or meta about an iterable)
            if isinstance(branch, nbt.TAG_End):
                name = ""
                value = ""
            elif isinstance(branch, nbt.TagIterable):
                value = f"{len(branch.payload)} children"
                if isinstance(branch, nbt.TAG_List):
                    value += f" of type {nbt.TAG_TYPES[branch.tagID].__name__}"
            else:
                value = str(branch.payload)

        # Print multiple elements per-line
        elif multi_values_per_line:
            if values is None:
                values = []
            values.append("{:>3}".format(branch))
            if len(values) == max_values_per_line:
                tagtype = str(type(branch))
                value = ' '.join(values)
                line = line_template.format(f"{padding}{tagtype}", level, size, name, value)
                print(line)
                values = None
            continue

        # Primitive types
        else:
            tagtype = str(type(branch))
            name = ""
            value = branch

            if isinstance(branch, str):
                size = str(len(branch))
            elif isinstance(parent, nbt.TAG_List):
                size = str(nbt.TAG_TYPES[parent.tagID].width)

        line = line_template.format(f"{padding}{tagtype}", level, size, name, value)
        print(line)

        # Then print the branches of the branch:
        if isinstance(branch, nbt.Tag) and hasattr(branch.payload, "__iter__"):
            if not isinstance(branch.payload, str):
                print_nbt(branch.payload, level + 1, branch)
        elif hasattr(branch, "__iter__"):
            print_nbt(branch, level + 1, None)

    if values:
        tagtype = str(type(branch))
        value = ' '.join(values)
        line = line_template.format(f"{padding}{tagtype}", level, size, name, value)
        print(line)


def print_nbt_file(filename: str):
    tree = None

    # Region/Anvil or pure NBT (compressed or not) accepted
    if filename.endswith(".mcr") or filename.endswith(".mca"):
        r = region.deserialize_file(filename)
        print(f"REGION {r.x} {r.z} stores {len(list(r))} chunks")
        tree = r  # __iter__() generator that yields chunks
    else:
        tree = nbt.deserialize_file(filename)

    print("{:<32} {:>3} {:>5}  {:>24} = {}".format(f"TYPE", "LVL", "SIZE", "NAME", "VALUE"))
    print('-' * (32 + 1 + 3 + 1 + 5 + 2 + 24 + 2))
    print_nbt(tree)


def main():
    # nbtviewer.py <filename>
    try:
        filename = sys.argv[1]
    except IndexError:
        print("! filename required")
        sys.exit(1)

    try:
        print_nbt_file(filename)
    except BrokenPipeError:
        pass  # permits e.g. `nbtviewer <file> | head`


if __name__ == "__main__":
#    sys.setrecursionlimit(3000000)
    main()
