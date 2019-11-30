# -*- coding: utf-8 -*-
""" NBT Serializer and Deserializer

This was a midnight programming experiment started with the goal of viewing and
editing a Minecraft 1.1 level.dat. The implementation is based on the
descriptions of the NBT file layout from these two docs:

https://web.archive.org/web/20191006152706/https://minecraft.gamepedia.com/NBT_format
https://web.archive.org/web/20110723210920/http://www.minecraft.net/docs/NBT.txt

Short summary:

    - The documentation is fuzzy about definitions. There are some guesses and
      assumptions built into this that aren't spelled out in the docs. It seems
      to work :) To elaborate...

    - NBT is conceptually about "tags", which are a triple of data. See the Tag
      class's tid, name, and payload attributes. The documentation sometimes
      uses the names of specific tags (e.g. TAG_String, TAG_Int, etc) to refer
      to the size of attributes or size of elements of an array rather than
      literally the three attributes (id, name, payload) packed together. For
      example, a TAG_String in Markus' txt spec has a "length" attribute
      defined as a "TAG_Short". The length attribute is just a `short`, or 2
      8-bit bytes. He could have just said "it's 16 bits", but whatever- baby's
      first data serialization format lol. TAG_End is another example of a tag
      which breaks the general format (id, name, payload).  This tag is just a
      single zero-valued byte (0x00). There's no name or payload.

    - Files that use NBT create a tree structure. The spec doesn't not clarify
      what kind of tree. In practice, there is one root which is always the
      TAG_Compound tag type. My implementation permits multiple roots.

This was written and tested using Python 3.6
"""

from typing import Any, Dict, List, Tuple


class Tag:

    tid: int = None
    name: str = None
    payload: Any = None

    def __init__(self, nbt_data: bytes = None, attrs: Tuple[str, Any] = None, named: bool = True, tagged: bool = True):
        """ Instantiation for all decendent tag types

        The purpose of this method is to populate the three tag attributes (id,
        name, and payload). Additional attributes are set for programmer
        convinience. The "name" and "payload" attributes are populated based on
        data in the byte array "nbt_data".
        
        Args:

            tagID::int
                The numeric identifier of the tag that's used as a key into
                TAG_TYPES to get the specific tag class.

            nbt_data::bytes
                If this parameter is not None, then the name and payload
                attributes will be determined by deserialization.

                This is the binary/bytes representation of this object as it
                appears in a decompressed NBT file. During deserialization,
                this is passed a slice of bytes of the total decompressed NBT
                file where the 0th index is the start of meaningful data for
                this tag. For example, nbt_data[0] is usually the tag id byte.
                The exact value depends on the context...

            attrs::Tuple[str, Any]
                If this parameter is not None, then the name and payload
                attrbiutes will be set according to the elements of the tuple.
                Deserialization will be skipped, even if the nbt_data parameter
                is not None.

            named::bool
                Does the tag have bytes in nbt_data corresponding to the name attribute?

            tagged::bool
                Does the tag have bytes in nbt_data corresponding to the tid attribute?

        Note that TAG_End is a special case of just a single byte of zero. You
        can think of it as a tag without bytes in nbt_data corresponding to the
        name or payload attributes.
        """
        self.nbt_data: bytes = nbt_data
        self.attrs: Tuple[str, Any] = attrs
        self.named: bool = named
        self.tagged: bool = tagged

        # The tag id is found by looking up the specific tag type in the tag id
        # to tag type mapping.
        for tag_id, tag_class in TAG_TYPES.items():
            if isinstance(self, tag_class):
                self.tid = tag_id
                break
        else:
            # This is only reachable if there's a bug or if there is an attempt
            # to instantiate one of the parent tag classes.
            raise ValueError(f"No tag id is defined for an instance of {self}")

        # self.size is used as an index into self.nbt_data in each
        # deserialize_* method. When each method is done processing a block of
        # bytes, the method calls self.checkpoint() to increment the value of
        # self.size by the number of bytes processed. That way, the next code
        # to process a block of bytes can use nbt_data[self.size:] to skip
        # bytes that have already been processed. The other purpose of
        # self.size is of course to get the total number of bytes the tag takes
        # up in the NBT file.
        self.size: int = 0
        self._prev_size: int = 0  # used for sanity checking

        # End tags are basically a tag id without a name or payload
        if isinstance(self, TAG_End):
            self.size = 1  # 1 byte processed (tag id)
            return

        # Tags in lists don't have a tag id byte.
        if tagged:
            self.size += 1  # 1 byte processed (tag id)

        # If all attributes are known ahead of time, then skip deserialization
        # of nbt_data (which is probably None if attrs is not None).
        if attrs is not None:
            name, payload = attrs
            self.name = name
            self.payload = payload
            self.size = len(self.serialize())
            return

        # If there's nothing to deserialize, then the name and payload
        # attributes can't be computed.
        if nbt_data is None:
            return

        if named:
            self.deserialize_name()
            assert self.size - self._prev_size >= 2  # all strings use at least two bytes
        else:
            # Tags in lists don't have a name.
            self.name = ""

        # Reminder: Payload parsing may recurse!
        self.deserialize_payload()
        assert self.size - self._prev_size >= 1  # all payloads use at least one byte


    def deserialize_name(self):
        """ Sets the name attribute
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

        # NOTE: I've yet to define whether name or payload for TAG_String
        # with a value of None has any semantic difference from emptry-string.
        # As of writing this comment, a None-valued attribute just means the
        # tag is "unnamed"; but we save the "named" attribute so that there's
        # no ambiguity.
        if string_size == 0:
            self.name = ""
            return

        self.name = self.nbt_data[self.size:self.size + string_size].decode('utf-8')
        self.checkpoint(string_size)

    def deserialize_payload(self):
        """ Sets the payload attribute

        This is specific to each tag and implemented in the respective tag class.
        """
        raise NotImplementedError

    def serialize(self) -> bytes:
        """ Returns this tag's representation in bytes
        """        
        # Special-case: TAG_End is defined as 0x00
        if isinstance(self, TAG_End):
            return b'\x00'

        # The tag needs to atleast have been initialized!
        assert self.tid is not None
        assert self.named is not None
        assert self.tagged is not None

        data = b''
        data += self.serialize_tid()
        data += self.serialize_name()
        data += self.serialize_payload()
        return data

    def serialize_tid(self) -> bytes:
        """ Convert the tag's id into its representation in bytes
        """
        if not self.tagged:
            return b''
        return self.tid.to_bytes(1, byteorder='big', signed=False)

    def serialize_name(self) -> bytes:
        """ Convert the tag's name into its representation in bytes

        The tag name is one or two parts. The first part is two bytes
            representing the length of the string, and then second is the
            actual bytes of the string (utf-8 encoded).
        """
        if not self.named:
            return b''

        encoded_string = self.name.encode('utf-8')
        encoded_length = len(encoded_string).to_bytes(2, byteorder='big', signed=False)
        return encoded_length + encoded_string

    def serialize_payload(self) -> bytes:
        """ Convert the tag's payload into its presentation in bytes

        This is specific to each tag and implemented in the respective tag class.
        """
        raise NotImplementedError

    def checkpoint(self, amount: int):
        """ Increase the value of self.size by some amount
        """
        self._prev_size = self.size
        self.size += amount


class TAG_End(Tag):
    """ Special-case; see the __init__ of Tag """


class TagInt(Tag):
    """ Parent-class for tags with an integer-typed payload
    """

    payload: int = None
    width: int = None

    def deserialize_payload(self):
        self.payload = int.from_bytes(
            self.nbt_data[self.size:self.size+self.width],
            byteorder='big',
            signed=True
        )
        self.checkpoint(self.width)

    def serialize_payload(self) -> bytes:
        return self.payload.to_bytes(self.width, byteorder='big', signed=True)


class TAG_Byte(TagInt):
    width = 1


class TAG_Short(TagInt):
    width = 2


class TAG_Int(TagInt):
    width = 4


class TAG_Long(TagInt):
    width = 8


class TagFloat(Tag):
    """ Parent class for floating point tag types
    """

    payload: bytes = None  # TODO make this a float
    width: int = None

    def deserialize_payload(self):
        # TODO cast this value to a float
        self.payload = self.nbt_data[self.size:self.size + self.width]
        self.checkpoint(self.width)

    def serialize_payload(self) -> bytes:
        # TODO actual deserialization of a float
        return self.payload


class TAG_Float(TagFloat):
    width = 4


class TAG_Double(TagFloat):
    width = 8


class TagIterable(Tag):
    """ Parent-class for tags with an iterable payload

    Use for tags where the payload is defined as an "array" in the NBT spec.

    The spec defines the payload as being an array of packed tags without an id
        or name field. This module uses types optimized for Python. For example,
        TAG_Byte_Array's payload is a list of bytes rather than a list of id-less &
        nameless TAG_Byte instances.

    By definition, TAG_String is not considered iterable since it's payload is
        not defined as an array in the spec. It therefore does not decend from this
        class despite having a "string_size_width" attribute which is identical in
        function to the "array_size_width" attribute.
    """

    # Number of bytes that represent the number of elements in the iterable (if
    # a length field is provided by the tag at all, e.g. TAG_Compound uses
    # TAG_End to denote the end of its array).
    array_size_width: int = None


class TAG_Byte_Array(TagIterable):

    array_size_width = 4  # int
    payload: List[bytes] = None

    def deserialize_payload(self):
        self.payload = []
        array_size = int.from_bytes(
            self.nbt_data[self.size:self.size + self.array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(self.array_size_width)

        # Straight-forward walk of each byte, appending to the payload array.
        for _ in range(array_size):
            self.payload.append(self.nbt_data[self.size:self.size + 1])
            self.checkpoint(1)

    def serialize_payload(self) -> bytes:
        data = len(self.payload).to_bytes(self.array_size_width, byteorder='big', signed=False)
        for b in self.payload:
            data += b
        return data


class TAG_String(Tag):

    payload: str = None
    string_size_width: int = 2  # short

    def deserialize_payload(self):
        string_size = int.from_bytes(
            self.nbt_data[self.size:self.size + self.string_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(self.string_size_width)

        if string_size == 0:
            self.payload = ""
            return

        self.payload = self.nbt_data[self.size:self.size + string_size].decode('utf-8')
        self.checkpoint(string_size)

    def serialize_payload(self) -> bytes:
        data = b''
        data += len(self.payload).to_bytes(self.string_size_width, byteorder='big', signed=False)
        data += self.payload.encode('utf-8')
        return data


class TAG_List(TagIterable):

    array_size_width = 4  # int
    tagID: int = None  # "A list with tags having a tid of tagID"
    payload: List[Tag] = None

    def __init__(self, *args, tagID: int = None, **kwargs,):
        """
        The "tagID" attribute (as its called in the spec) is unique to
            TAG_List. The value gives the type of the tags stored in the payload.
            An empty Python list drops this information (which could be recovered
            by otherwise looking at the first element of the list).

        self.serialize() will fail with an AssertionError if this attribute is
            not set and the payload is an empty list!
        """
        self.tagID = tagID
        super(TAG_List, self).__init__(*args, **kwargs)

    def deserialize_payload(self):
        self.payload = []

        # Determine the tag type; this only gives us the class to instantiate
        tag_id = self.nbt_data[self.size:self.size + 1][0]
        self.tagID = tag_id  # save for serialization
        self.checkpoint(1)

        # Determine the eventual number of elements in the list
        array_size = int.from_bytes(
            self.nbt_data[self.size:self.size + self.array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(self.array_size_width)

        # The size of each tag isn't known ahead of time. All we know is that
        # we need to append `array_size` tags to the list. Successive offsets
        # into the data are determined by the sum of the sizes of the
        # previously deserialized tags.
        for _ in range(array_size):
            tag = TAG_TYPES[tag_id](self.nbt_data[self.size:], named=False, tagged=False)
            self.payload.append(tag)
            self.checkpoint(tag.size)

    def serialize_payload(self) -> bytes:
        # See the docstring for TAG_List's constructor.
        assert self.tagID or self.payload

        # self.tagID will not have been set if deserialization was skipped. We
        #   can recover it by looking at the first element of the list.
        if not self.tagID:
            self.tagID = self.payload[0].tid

        data = b''
        data += self.tagID.to_bytes(1, byteorder='big', signed=False)
        data += len(self.payload).to_bytes(self.array_size_width, byteorder='big', signed=False)
        for tag in self.payload:
            data += tag.serialize()
        return data


class TAG_Compound(TagIterable):

    payload: List[Tag] = None

    def deserialize_payload(self):
        self.payload = []
        while True:
            tag_id = self.nbt_data[self.size:][0]
            tag = TAG_TYPES[tag_id](self.nbt_data[self.size:])
            self.checkpoint(tag.size)
            self.payload.append(tag)
            if isinstance(tag, TAG_End):
                break

    def serialize_payload(self) -> bytes:
        assert isinstance(self.payload[-1], TAG_End)
        data = b''
        for tag in self.payload:
            data += tag.serialize()
        return data


class TagIterableNumeric(TagIterable):
    """ Parent-class for lists of numerics
    """

    array_size_width = 4  # int
    payload: List[int] = None
    width = None

    def deserialize_payload(self):
        self.payload = []

        # Determine the eventual number of elements in the list
        array_size = int.from_bytes(
            self.nbt_data[self.size:self.size + self.array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(self.array_size_width)

        # Straight-forward walk of each int/long, appending to the payload array.
        for _ in range(array_size):
            int_value = int.from_bytes(
                self.nbt_data[self.size:self.size + self.width],
                byteorder='big',
                signed=True
            )
            self.payload.append(int_value)
            self.checkpoint(self.width)

    def serialize_payload(self) -> bytes:
        data = b''
        data += len(self.payload).to_bytes(self.array_size_width, byteorder='big', signed=False)
        for numeric in self.payload:
            data += numeric.to_bytes(
                self.width,
                byteorder='big',
                signed=True
            )
        return data


class TAG_Int_Array(TagIterableNumeric):
    width = 4  # int


class TAG_Long_Array(TagIterableNumeric):
    width = 8  # long


TAG_TYPES: Dict[int, Tag] = {
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


def deserialize(nbt_data: bytes) -> List[Tag]:
    """ Deserialize NBT data and return a tree
    """
    nbt_tree = []
    total_bytes = len(nbt_data)

    # Each iteration of this loop processes one tag at the root of the tree.
    #
    # If there's only one root, the value of tag.size is equal to the total
    # size (in bytes) of the data itself (since the one and only root tag
    # comprises the entire data). If not, the bytes following the tag are
    # considered a new tag.
    remaining_bytes = total_bytes
    while remaining_bytes > 0:

        index = total_bytes - remaining_bytes
        tag_id = nbt_data[index:][0]
        tag = TAG_TYPES[tag_id](nbt_data[index:])

        # This assert prevents the while loop from spinning forever in the
        # highly-unlikely event of tag.size being zero or negative (most likely
        # due to a bug).
        assert tag.size >= 1

        remaining_bytes -= tag.size
        nbt_tree.append(tag)

    return nbt_tree


def serialize(nbt_tree: List[Tag]) -> bytes:
    """ Serialize an NBT tree and return uncompressed bytes
    """
    data = b''
    for tag in nbt_tree:
        data += tag.serialize()
    return data


def deserialize_file(filename: str) -> List[Tag]:
    """ Deserialize a GZip compressed or uncompressed NBT file
    """
    with open(filename, 'rb') as nbt_file:
        file_data = nbt_file.read()

    # The file may or may not be compressed. Check for the magic number to know!
    # https://www.onicos.com/staff/iz/formats/gzip.html
    if file_data[0:2] == b'\x1f\x8b':
        import gzip
        decompressed_data: bytes = gzip.decompress(file_data)
        return deserialize(decompressed_data)

    return deserialize(file_data)


def serialize_file(filename: str, nbt_tree: List[Tag], compress: bool = True):
    """ Serialize an NBT tree, optionally compress the output, and to a file
    """
    data: bytes = serialize(nbt_tree)
    if compress:
        import gzip
        data = gzip.compress(data)
    with open(filename, 'wb') as f:
        f.write(data)
