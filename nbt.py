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

        # End tags are basically a tag id without a name or payload
        if isinstance(self, TAG_End):
            self.size = 1
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
        string_size_width = 2  # length defined by a short
        string_size = int.from_bytes(
            self.nbt_data[self.size:self.size + string_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(string_size_width)

        # NOTE: I've yet to define whether TagName or TagPayload for TAG_String
        # with a value of None has any semantic difference from emptry-string.
        # As of writing this comment, a None-valued attribute just means the
        # tag is "unnamed"; but we save the "named" attribute so that there's
        # no ambiguity.
        if string_size == 0:
            self.TagName = ""
            return

        self.TagName = self.nbt_data[self.size:self.size + string_size].decode('utf-8')
        self.checkpoint(string_size)

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

    width: int = None

    def parse_payload(self):
        # TODO cast this value to a float
        self.TagPayload = self.nbt_data[self.size:self.size + self.width]
        self.checkpoint(self.width)


class TAG_Float(TagFloat):
    width = 4


class TAG_Double(TagFloat):
    width = 8


class TagIterable(TagType):
    pass


class TAG_Byte_Array(TagIterable):
    
    def parse_payload(self):
        self.TagPayload: List[bytes] = []
        array_size_width = 4  # an int provides the array length
        array_size = int.from_bytes(
            self.nbt_data[self.size:self.size + array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(array_size_width)

        # Straight-forward walk of each byte, appending to the payload array.
        for _ in range(array_size):
            self.TagPayload.append(self.nbt_data[self.size:self.size + 1])
            self.checkpoint(1)


class TAG_String(TagType):

    def parse_payload(self):
        string_size_width = 2  # a short provides the string length
        string_size = int.from_bytes(
            self.nbt_data[self.size:self.size + string_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(string_size_width)

        if string_size == 0:
            self.TagPayload = ""
            return

        self.TagPayload = self.nbt_data[self.size:self.size + string_size].decode('utf-8')
        self.checkpoint(string_size)


class TAG_List(TagIterable):

    def parse_payload(self):
        self.TagPayload: List[TagType] = []

        # First, which determine the tag class:
        tag_id_width = 1  # byte
        tag_id = self.nbt_data[self.size:self.size + tag_id_width][0]
        self.checkpoint(tag_id_width)

        # Second, determine how many of each tag class:
        array_size_width = 4  # int
        array_size = int.from_bytes(
            self.nbt_data[self.size:self.size + array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(array_size_width)

        # The implementation here is a first guess of how Markus implemented
        # lists. I'm assuming the payload of each tag is back-to-back. That is,
        # it's just a compound tag without the tag id or name preceeding the
        # element.
        for index in range(array_size):
            tag = TAG_TYPES[tag_id](tag_id, self.nbt_data[self.size:], named=False, tagged=False)
            self.checkpoint(tag.size)


class TAG_Compound(TagIterable):

    def parse_payload(self):
        self.TagPayload: List[TagTypes] = []
        while True:
            tag_id = self.nbt_data[self.size:][0]
            tag = TAG_TYPES[tag_id](tag_id, self.nbt_data[self.size:])
            self.checkpoint(tag.size)
            self.TagPayload.append(tag)

            # Break out if we reached a TAG_End!
            #   This tag type never appears at the root of the tree unless the file
            #   is corrupted. If we reach this point, we're probably processing on
            #   behalf of a compound tag.
            if isinstance(tag, TAG_End):
                break


class TAG_Int_Array(TagIterable):

    def parse_payload(self):
        self.TagPayload: List[int] = []
        array_value_width = 4  # we're creating a list of ints
        array_size_width = 4   # an int provides the array length
        array_size = int.from_bytes(
            self.nbt_data[self.size:self.size + array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(array_size_width)

        # Straight-forward walk of each int, appending to the payload array.
        for _ in range(array_size):
            int_value = int.from_bytes(
                self.nbt_data[self.size:self.size + array_value_width],
                byteorder='big',
                signed=False
            )
            self.TagPayload.append(int_value)
            self.checkpoint(array_value_width)


class TAG_Long_Array(TagIterable):

    def parse_payload(self):
        self.TagPayload: List[int] = []
        array_value_width = 8  # we're creating a list of longs
        array_size_width = 4   # an int provides the array length
        array_size = int.from_bytes(
            self.nbt_data[self.size:self.size + array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(array_size_width)

        # Straight-forward walk of each int, appending to the payload array.
        for _ in range(array_size):
            int_value = int.from_bytes(
                self.nbt_data[self.size:self.size + array_value_width],
                byteorder='big',
                signed=False
            )
            self.TagPayload.append(int_value)
            self.checkpoint(array_value_width)


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
