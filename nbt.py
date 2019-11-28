# -*- coding: utf-8 -*-
""" NBT Serializer and Deserializer

This was a midnight programming experiment started with the goal of viewing and
editing a Minecraft 1.1 level.dat. The implementation is based on the
descriptions of the NBT file layout from these two docs:

https://web.archive.org/web/20191006152706/https://minecraft.gamepedia.com/NBT_format
https://web.archive.org/web/20110723210920/http://www.minecraft.net/docs/NBT.txt

Short summary:

    - NBT files are GZip compressed. In order to work with the data inside,
      they must obviously be decompressed. This module accepts either a
      filename which contains compressed data, or a blob of decompressed data.

    - The documentation is fuzzy about definitions and I haven't searched for
      whether Mojang provides any kind of implementation guidelines. There are
      some guesses and assumptions built into this that aren't spelled out in
      the docs. It seems to work :) To elaborate...

    - NBT is conceptually about "tags", which are a triple of data. See the
      TagType class's TagID, TagName, and TagPayload attributes. The
      documentation sometimes uses the names of specific tags (e.g. TAG_String,
      TAG_Int, etc) to refer to the size of attributes or size of elements of
      an array rather than literally the three attributes (id, name, payload)
      packed together. For example, a TAG_String in Markus' txt spec has a
      "length" attribute defined as a "TAG_Short". The length attribute is just
      a `short`, or 2 8-bit bytes. He could have just said "it's 16 bits", but
      whatever- baby's first data serialization format lol. TAG_End is another
      example of a tag which breaks the general format (id, name, payload).
      This tag is just a single zero-valued byte (0x00).  There's no name or
      payload.

    - Files that use NBT create a tree structure. The spec doesn't not clarify
      what kind of tree. In practice, there is one root which is always the
      TAG_Compound tag type. My implementation permits multiple roots.

This was written and tested using Python 3.6
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
            self.deserialize_name()
            assert self.size - self._prev_size >= 2

        # Reminder: Payload parsing may recurse!
        self.deserialize_payload()
        assert self.size - self._prev_size >= 1


    def deserialize_name(self) -> None:
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

    def deserialize_payload(self) -> int:
        raise NotImplementedError

    def checkpoint(self, amount: int):
        """ Increase the value of self.size by some amount
        """
        self._prev_size = self.size
        self.size += amount


class TAG_End(TagType):
    """ Special-case; see the __init__ of TagType """


class TagInt(TagType):
    """ Parent-class for tags with an integer-typed payload
    """

    width: int = None

    def deserialize_payload(self):
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

    def deserialize_payload(self):
        # TODO cast this value to a float
        self.TagPayload = self.nbt_data[self.size:self.size + self.width]
        self.checkpoint(self.width)


class TAG_Float(TagFloat):
    width = 4


class TAG_Double(TagFloat):
    width = 8


class TagIterable(TagType):
    """ Parent-class for tags with an iterable payload
    """


class TAG_Byte_Array(TagIterable):
    
    def deserialize_payload(self):
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

    def deserialize_payload(self):
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

    def deserialize_payload(self):
        self.TagPayload: List[TagType] = []

        # Determine the tag type; this only gives us the class to instantiate
        tag_id_width = 1  # byte
        tag_id = self.nbt_data[self.size:self.size + tag_id_width][0]
        self.checkpoint(tag_id_width)

        # Determine the eventual number of elements in the list
        array_size_width = 4  # int
        array_size = int.from_bytes(
            self.nbt_data[self.size:self.size + array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(array_size_width)

        # The size of each tag isn't known ahead of time. All we know is that
        # we need to append `array_size` tags to the list. Successive offsets
        # into the data are determined by the sum of the sizes of the
        # previously deserialized tags.
        for _ in range(array_size):
            tag = TAG_TYPES[tag_id](tag_id, self.nbt_data[self.size:], named=False, tagged=False)
            self.TagPayload.append(tag)
            self.checkpoint(tag.size)


class TAG_Compound(TagIterable):

    def deserialize_payload(self):
        self.TagPayload: List[TagTypes] = []
        while True:
            tag_id = self.nbt_data[self.size:][0]
            tag = TAG_TYPES[tag_id](tag_id, self.nbt_data[self.size:])
            self.checkpoint(tag.size)
            self.TagPayload.append(tag)
            if isinstance(tag, TAG_End):
                break


class TagIterableNumeric(TagIterable):
    """ Parent-class for lists of numerics
    """

    width = None

    def deserialize_payload(self):
        self.TagPayload: List[int] = []

        # Determine the eventual number of elements in the list
        array_size_width = 4   # int
        array_size = int.from_bytes(
            self.nbt_data[self.size:self.size + self.width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(array_size_width)

        # Straight-forward walk of each int/long, appending to the payload array.
        for _ in range(array_size):
            int_value = int.from_bytes(
                self.nbt_data[self.size:self.size + self.width],
                byteorder='big',
                signed=False
            )
            self.TagPayload.append(int_value)
            self.checkpoint(self.width)


class TAG_Int_Array(TagIterableNumeric):
    width = 4  # int


class TAG_Long_Array(TagIterableNumeric):
    width = 8  # long


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


def deserialize(nbt_data: bytes) -> List[TagType]:
    """ Deserialize NBT data and return a tree
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


def deserialize_file(filename: str) -> List[TagType]:
    """ Deserialize a GZip compressed NBT file
    """

    # Take a compressed file and extract the compressed data
    with open(filename, 'rb') as compressed_nbt_file:
        compressed_nbt_data = compressed_nbt_file.read()

    # Decompress the data
    decompressed_nbt_data = gzip.decompress(compressed_nbt_data)

    # Deserialize the data
    return deserialize(decompressed_nbt_data)
