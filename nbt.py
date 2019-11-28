""" NBT File Format Parser
2019 Seth Junot (xsetech@gmail.com)
"""

import gzip
from typing import Any, Dict, List, Tuple


class TagType:

    TagID: int = None
    TagName: str = None
    TagPayload: Any = None

    def __init__(self, nbt_data: bytes):
        """ Just save a reference to the bytes slice
        """
        self.nbt_data = nbt_data
        self.parse_name()
        self.parse_payload()

    def parse_name(self):
        """ This is the same for all tags!
        """

    def parse_payload(self):
        raise NotImplementedError


class TAG_End(TagType):
    pass


class TAG_Byte(TagType):
    pass


class TAG_Short(TagType):
    pass


class TAG_Int(TagType):
    pass


class TAG_Long(TagType):
    pass


class TAG_Float(TagType):
    pass


class TAG_Double(TagType):
    pass


class TAG_Byte_Array(TagType):
    pass


class TAG_String(TagType):
    pass


class TAG_List(TagType):
    pass


class TAG_Compound(TagType):
    pass


class TAG_Int_Array(TagType):
    pass


class TAG_Long_Array(TagType):
    pass


TAG_TYPES: Dict[int, TagType] = {
    0x00: TAG_End,
    0x01: TAG_Byte,
    0x02: TAG_Short,
    0x03: TAG_Int,
    0x04: TAG_Long,
    0x05: TAG_Float,
    0x06: TAG_Double,
    0x07: TAG_Byte_Array,
    0x08: TAG_String,
    0x09: TAG_List,
    0x0a: TAG_Compound,
    0x0b: TAG_Int_Array,
    0x0c: TAG_Long_Array
}


def create_tag(nbt_data: bytes) -> Tuple[TagType, int]:
    """ Instantiate a tag and return the size
    """
    # Get the tag class using the first byte from the index and decrement
    # remaining_bytes since the first byte is no longer needed.
    tag_id = nbt_data[0]
    tag = TAG_TYPES[tag_id]
    return 1 + TAG_TYPES[tag_id](nbt_data).parse()


# Actual work is done in here.
def _parse(nbt_data: bytes) -> List[TagType]:
    """ Parse NBT data and return a tree

    All parse() methods for container types eventually call this.
    """
    nbt_tree = []  # this gets returned
    total_bytes = len(nbt_data)
    remaining_bytes = total_bytes
    while remaining_bytes > 0:
        index = total_bytes - remaining_bytes
        tag, parsed_bytes = create_tag(nbt_data[index:])
        assert parsed_bytes >= 1  # we at least read the tag id
        remaining_bytes -= parsed_bytes
        nbt_tree.append(tag)
    return nbt_tree


# Start here.
def parse(filename: str) -> List[TagType]:
    """ Parse a GZip compressed NBT file
    """

    # Take a compressed file and extract the compressed data
    with open(filename, 'rb') as compressed_nbt_file:
        compressed_nbt_data = compressed_nbt_file.read()

    # Decompress the data
    decompressed_nbt_data = gzip.decompress(compressed_nbt_data)

    # Parse the data
    #
    #   The root node is special; it's always a compound tag.
    #   Get the first byte from the decompressed data, lookup the tag type, and
    #   instantiate it. Pass the array of bytes into the type's "parse" method.
    #   The parse method will return the number of bytes parsed. Subtract from
    #   the total bytes to parse and continue until the value reaches zero.
    return _parse(decompressed_nbt_data)
