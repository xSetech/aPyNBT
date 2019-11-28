""" NBT File Format Parser
2019 Seth Junot (xsetech@gmail.com)
"""

import gzip
from typing import Any, Dict, List, Tuple


class TagType:

    TagID: int = None
    TagName: str = None
    TagPayload: Any = None

    def __init__(self, tagID: int, nbt_data: bytes, named: bool = True, tagged: bool = True):
        """ Just save a reference to the bytes slice
        """
        self.TagID = tagID
        self.nbt_data: bytes = nbt_data
        self.named: bool = named
        self.tagged: bool = tagged

        # Note: The size is used as an index for each method.
        self.size: int = 0
        self._prev_size: int = 0  # used for sanity checking

        # End tags don't have a name or payload field
        if isinstance(self, TAG_End):
            return

        # Tags in lists don't have a tag id byte.
        if tagged:
            self.size += 1  # 1 byte processed (tag id)

        # Tags in lists don't have a name.
        if named:
            self.parse_name()
            assert self.size - self._prev_size >= 2

        # Reminder: Payload parsing may recurse!
        self.parse_payload()
        assert self.size - self._prev_size >= 1


    def parse_name(self) -> None:
        """ Sets the TagName attribute

        Returns 2 + (size of string as specific by the two bytes)
        """
        # The size of the name is give by two Big Endian bytes, offset one from
        # the first byte (the tag id).
        string_size = int.from_bytes(
            self.nbt_data[self.size:self.size+2],
            byteorder='big',
            signed=False
        )

        # If the string size is 0, consider the name to be ""
        if string_size == 0:
            self.TagName = ""
            self.checkpoint(2)

        # Otherwise, interpret the string name as UTF-8
        string_index_start = self.size + 2
        string_index_stop = string_index_start + string_size
        self.TagName = self.nbt_data[string_index_start:string_index_stop].decode('utf-8')

        self.checkpoint(2 + string_size)

    def parse_payload(self) -> int:
        raise NotImplementedError

    def checkpoint(self, amount: int):
        """ Increase the value of self.size by some amount
        """
        self._prev_size = self.size
        self.size += amount


class TAG_End(TagType):
    """ Marks the end of a container or file """
    pass


class TagInt(TagType):
    """ Parent class for integer-ish tag types
    """

    width: int = None

    def parse_payload(self):
        self.TagPayload = int.from_bytes(
            self.nbt_data[self.size:self.size+self.width],
            byteorder='big',
            signed=True
        )
        self.checkpoint(self.width)


class TAG_Byte(TagInt):
    width = 1


class TAG_Short(TagInt):
    width = 2


class TAG_Int(TagInt):
    width = 4


class TAG_Long(TagInt):
    width = 8


class TagFloat(TagType):
    """ Parent class for floating point tag types
    """
    pass # TODO


class TAG_Float(TagFloat):
    pass


class TAG_Double(TagFloat):
    pass


class TAG_Byte_Array(TagType):
    
    def parse_payload(self):
        self.TagPayload: List[bytes] = []
        array_size_width = 4  # an int provides the array length
        array_size = int.from_bytes(
            self.nbt_data[self.size:self.size + array_size_width],
            byteorder='big',
            signed=False
        )

        # Straight-forward walk of each byte, appending to the payload array.
        array_index_start = self.size + array_size_width  # after the provided length
        for index in range(array_size):
            self.TagPayload.append(self.nbt_data[array_index_start:array_index_start + index + 1])
        
        self.checkpoint(array_size_width + array_size)


class TAG_String(TagType):

    def parse_payload(self):
        string_size_width = 2  # a short provides the string length
        string_size = int.from_bytes(
            self.nbt_data[self.size:self.size + string_size_width],
            byteorder='big',
            signed=False
        )

        # Empty strings do not have payloads
        if string_size == 0:
            self.checkpoint(string_size_width)

        string_index_start = self.size + string_size_width
        string_index_stop = string_index_start + string_size
        self.TagPayload = self.nbt_data[string_index_start:string_index_stop].decode('utf-8')

        self.checkpoint(string_size_width + string_size)


class TAG_List(TagType):

    def parse_payload(self):
        self.TagPayload: List[TagType] = []

        # First, which determine the tag class:
        tag_id_width = 1  # byte
        tag_id = self.nbt_data[self.size:self.size + tag_id_width]

        # Second, determine how many of each tag class:
        array_size_width = 4  # int
        array_size_index_start = self.size + tag_id_width
        array_size_index_stop = array_size_index_start + array_size_width
        array_size = int.from_bytes(
            self.nbt_data[array_size_index_start:array_size_index_stop],
            byteorder='big',
            signed=False
        )

        # The implementation here is a first guess of how Markus implemented
        # lists. I'm assuming the payload of each tag is back-to-back. That is,
        # it's just a compound tag without the tag id or name preceeding the
        # element.
        offset = array_size_index_stop
        for index in range(array_size):
            tag = TAG_TYPES[tag_id](tag_id, self.nbt_data[offset:], named=False, tagged=False)
            offset += tag.size

        self.checkpoint(offset)


class TAG_Compound(TagType):

    def parse_payload(self):
        self.TagPayload = _parse(self.nbt_data[self.size:])
        self.checkpoint(sum([tag.size for tag in self.TagPayload]))


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
        tag_id = nbt_data[index:][0]
        tag = TAG_TYPES[tag_id](tag_id, nbt_data[index:])
        remaining_bytes -= tag.size
        nbt_tree.append(tag)

        # Break out if we reached a TAG_End!
        #   This tag type never appears at the root of the tree unless the file
        #   is corrupted. If we reach this point, we're probably processing on
        #   behalf of a compound tag.
        if isinstance(tag, TAG_End):
            break

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
