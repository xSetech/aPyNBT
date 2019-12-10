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
    """ Base class of all tags """

    # "tag id", an immutable attribute of a specific subclass of Tag
    tid: int = None

    # "name" and "payload" are mutable instance attributes collected either by
    # deserialization of nbt data or by having them passed as arguments to the
    # constructor.
    name: str = None
    payload: Any = None

    def __init__(self, nbt_data: bytes = None, name: str = None, payload: Any = None, named: bool = None, tagged: bool = True):
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
                attributes will be determined by deserialization. Otherwise,
                deserialization of either attribute will be skipped.

                This is at least the binary/bytes representation of a tag
                instance as it appears in a decompressed NBT file. Unused or
                unrelated bytes are permitted at the end. Therefore, in
                particular during deserialization, this *is not* the same as
                the return value from the serialize() method.

            name::str
                If this parameter is not None, then the tag's "name" attribute
                will be set to this value.

            payload::Any
                If this parameter is not None, then the tag's "payload"
                attribute will be set to this value.

            named::bool
                If deserializing, indicates the tag has bytes in nbt_data
                corresponding to the "name" attribute. If serializing, bytes
                will be created to represent the attribute (a value of None
                will be treated as an empty string).

            tagged::bool
                If deserializing, indicates the tag has bytes in nbt_data
                corresponding to the "tid" attribute. If serializing, bytes
                will be created to represent the attribute.

        Note that TAG_End is a special case of just a single byte of zero. You
        can think of it as a tag without bytes in nbt_data corresponding to the
        name or payload attributes.
        """
        self.tagged: bool = tagged

        # If named is explicitly given, we'll use the passed value. Otherwise,
        # the value is inferred from other arguments.
        if named is not None:
            self.named: bool = named
        else:
            if nbt_data is not None:
                self.named = True
            else:
                if name is None:
                    self.named = False
                else:
                    self.named = True

        # self._size is the number of bytes processed during deserialization.
        # It's incremented by the checkpoint() method. If the value is zero,
        # then no deserialization has occured.
        self._size: int = 0
        self._prev_size: int = 0  # used for sanity checking

        # Special-case; TAG_End are basically a tag id without a name or payload
        if isinstance(self, TAG_End):
            self._size = 1  # 1 byte processed (tag id)
            return

        # If there's nothing to deserialize, then the name and payload
        # attributes can't be collected.
        if nbt_data is not None:
            self.deserialize(nbt_data)

        # Regardless of whether deserialization was skipped, if either "name"
        # or "payload" are passed as parameters, use them.
        if name is not None:
            self.name = name
        if payload is not None:
            self.payload = payload

        # Named tags with None-valued names are the same as empty-string valued
        # named tags.
        if self.named and self.name is None:
            self.name = ""

    def deserialize(self, data: bytes):
        """
        Deserialize a blob of data and set the `name` and `payload` attributes
            of the tag.
        """
        # Save the data so that deserialize_name() and deserialize_payload()
        # can reference it.
        self.nbt_data = data
        self._size = 0

        # Tags in lists don't have a tag id byte.
        if self.tagged:
            self._size += 1  # 1 byte processed (tag id)

        # Tags in lists don't have a name.
        if self.named:
            self.deserialize_name()
            assert self._size - self._prev_size >= 2  # all strings use at least two bytes
        else:
            self.name = ""

        # Reminder: Payload parsing may recurse!
        self.deserialize_payload()
        assert self._size - self._prev_size >= 1  # all payloads use at least one byte

    def deserialize_name(self):
        """ Sets the name attribute
        """
        # The size of the name is give by two Big Endian bytes, offset one from
        # the first byte (the tag id).
        string_size_width = 2  # length defined by a short
        string_size = int.from_bytes(
            self.nbt_data[self._size:self._size + string_size_width],
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

        self.name = self.nbt_data[self._size:self._size + string_size].decode('utf-8')
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

        # Can't serialize a base-class!
        assert self.tid is not None

        # The tag needs to at least have been initialized!
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

        # Named tags with None-valued names are the same as empty-string valued
        # named tags. These lines handle the case of an NBT editor accidentally
        # setting the attribute to None after instantiation.
        if self.name is None:
            self.name = ""

        encoded_string = self.name.encode('utf-8')
        encoded_length = len(encoded_string).to_bytes(2, byteorder='big', signed=False)
        return encoded_length + encoded_string

    def serialize_payload(self) -> bytes:
        """ Convert the tag's payload into its presentation in bytes

        This is specific to each tag and implemented in the respective tag class.
        """
        raise NotImplementedError

    def validate(self):
        """ Validate the current tag's payload

        No return value; an exception is raised if validation fails.
        Implementation is specific to each tag and implemented in the
        respective tag class.
        """
        raise NotImplementedError

    def checkpoint(self, amount: int):
        """ Increase the value of self._size by some amount
        """
        self._prev_size = self._size
        self._size += amount

    def __repr__(self) -> str:
        """ See https://docs.python.org/3.6/reference/datamodel.html#object.__repr__
        """
        return f"<{self.__class__} size={self._size} name='{self.name}' named={self.named} tagged={self.tagged}>"


class TAG_End(Tag):
    """ Special-case; see the __init__ of Tag """

    tid = 0x00


class TagInt(Tag):
    """ Parent-class for tags with an integer-typed payload
    """

    payload: int = None
    width: int = None

    def deserialize_payload(self):
        self.payload = int.from_bytes(
            self.nbt_data[self._size:self._size+self.width],
            byteorder='big',
            signed=True
        )
        self.checkpoint(self.width)

    def serialize_payload(self) -> bytes:
        return self.payload.to_bytes(self.width, byteorder='big', signed=True)

    def validate(self):
        assert isinstance(self.payload, int)
        self.payload.to_bytes(self.width, byteorder='big', signed=True)


class TAG_Byte(TagInt):

    tid = 0x01
    width = 1


class TAG_Short(TagInt):

    tid = 0x02
    width = 2


class TAG_Int(TagInt):

    tid = 0x03
    width = 4


class TAG_Long(TagInt):

    tid = 0x04
    width = 8


class TagFloat(Tag):
    """ Parent class for floating point tag types
    """

    payload: bytes = None  # TODO make this a float
    width: int = None

    def deserialize_payload(self):
        # TODO cast this value to a float
        self.payload = self.nbt_data[self._size:self._size + self.width]
        self.checkpoint(self.width)

    def serialize_payload(self) -> bytes:
        # TODO actual deserialization of a float
        return self.payload

    def validate(self):
        pass  # TODO


class TAG_Float(TagFloat):

    tid = 0x05
    width = 4


class TAG_Double(TagFloat):

    tid = 0x06
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

    tid = 0x07
    array_size_width = 4  # int
    payload: List[bytes] = None

    def deserialize_payload(self):
        self.payload = []
        array_size = int.from_bytes(
            self.nbt_data[self._size:self._size + self.array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(self.array_size_width)

        # Straight-forward walk of each byte, appending to the payload array.
        for _ in range(array_size):
            self.payload.append(self.nbt_data[self._size:self._size + 1])
            self.checkpoint(1)

    def serialize_payload(self) -> bytes:
        data = len(self.payload).to_bytes(self.array_size_width, byteorder='big', signed=False)
        for b in self.payload:
            data += b
        return data

    def validate(self):
        assert isinstance(self.payload, list)
        if self.payload:
            for value in self.payload:
                assert isinstance(value, bytes)
                assert len(value) == 1


class TAG_String(Tag):

    tid = 0x08
    payload: str = None
    string_size_width: int = 2  # short

    def deserialize_payload(self):
        string_size = int.from_bytes(
            self.nbt_data[self._size:self._size + self.string_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(self.string_size_width)

        if string_size == 0:
            self.payload = ""
            return

        self.payload = self.nbt_data[self._size:self._size + string_size].decode('utf-8')
        self.checkpoint(string_size)

    def serialize_payload(self) -> bytes:
        data = b''
        encoded_string = self.payload.encode('utf-8')
        data += len(encoded_string).to_bytes(self.string_size_width, byteorder='big', signed=False)
        data += encoded_string
        return data

    def validate(self):
        assert isinstance(self.payload, str)


class TAG_List(TagIterable):

    tid = 0x09
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
        tag_id = self.nbt_data[self._size:self._size + 1][0]
        self.tagID = tag_id  # save for serialization
        self.checkpoint(1)

        # Determine the eventual number of elements in the list
        array_size = int.from_bytes(
            self.nbt_data[self._size:self._size + self.array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(self.array_size_width)

        # The size of each tag isn't known ahead of time. All we know is that
        # we need to append `array_size` tags to the list. Successive offsets
        # into the data are determined by the sum of the sizes of the
        # previously deserialized tags.
        for _ in range(array_size):
            tag = TAG_TYPES[tag_id](self.nbt_data[self._size:], named=False, tagged=False)
            self.payload.append(tag)
            self.checkpoint(tag._size)

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

    def validate(self):
        assert isinstance(self.payload, list)
        if self.payload:
            for value in self.payload:
                assert value.__class__ in TAGS
                assert not value.named
                assert not value.tagged


class TAG_Compound(TagIterable):

    tid = 0x0a
    payload: List[Tag] = None

    def deserialize_payload(self):
        self.payload = []
        while True:
            tag_id = self.nbt_data[self._size:][0]
            tag = TAG_TYPES[tag_id](self.nbt_data[self._size:])
            self.checkpoint(tag._size)
            self.payload.append(tag)
            if isinstance(tag, TAG_End):
                break

    def serialize_payload(self) -> bytes:
        assert isinstance(self.payload[-1], TAG_End)
        data = b''
        for tag in self.payload:
            data += tag.serialize()
        return data

    def validate(self):
        assert isinstance(self.payload, list)
        if self.payload:
            for value in self.payload:
                assert value.__class__ in TAGS
        assert isinstance(self.payload[-1], TAG_End)


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
            self.nbt_data[self._size:self._size + self.array_size_width],
            byteorder='big',
            signed=False
        )
        self.checkpoint(self.array_size_width)

        # Straight-forward walk of each int/long, appending to the payload array.
        for _ in range(array_size):
            int_value = int.from_bytes(
                self.nbt_data[self._size:self._size + self.width],
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

    def validate(self):
        assert isinstance(self.payload, list)
        if self.payload:
            for value in self.payload:
                assert isinstance(value, int)
                value.to_bytes(self.width, byteorder='big', signed=True)


class TAG_Int_Array(TagIterableNumeric):

    tid = 0x0b
    width = 4  # int


class TAG_Long_Array(TagIterableNumeric):

    tid = 0x0c
    width = 8  # long


# Official "tags" as defined by the spec and Minecraft wiki.
#
# According to the wiki, some tags will only be seen from and usable on newer
#   versions of Minecraft. For the sake of simplicity, this module doesn't
#   account for NBT versions or Java-specific limitations.
TAGS: Tuple[Tag] = (
    TAG_End,
    TAG_Byte,
    TAG_Short,
    TAG_Int,
    TAG_Long,
    TAG_Float,
    TAG_Double,
    TAG_Byte_Array,
    TAG_String,
    TAG_List,
    TAG_Compound,
    TAG_Int_Array,
    TAG_Long_Array
)

# A mapping from tag id to tag classes is generally useful.
TAG_TYPES: Dict[int, Tag] = {
    tag_class.tid: tag_class for tag_class in TAGS
}


def deserialize(nbt_data: bytes) -> List[Tag]:
    """ Deserialize NBT data and return a tree
    """
    nbt_tree = []
    total_bytes = len(nbt_data)

    # Each iteration of this loop processes one tag at the root of the tree.
    #
    # If there's only one root, the value of tag._size is equal to the total
    # size (in bytes) of the data itself (since the one and only root tag
    # comprises the entire data). If not, the bytes following the tag are
    # considered a new tag.
    remaining_bytes = total_bytes
    while remaining_bytes > 0:

        index = total_bytes - remaining_bytes
        tag_id = nbt_data[index:][0]
        tag = TAG_TYPES[tag_id](nbt_data[index:])

        # This assert prevents the while loop from spinning forever in the
        # highly-unlikely event of tag._size being zero or negative (most likely
        # due to a bug).
        assert tag._size >= 1

        remaining_bytes -= tag._size
        nbt_tree.append(tag)

    return nbt_tree


def serialize(nbt_tree: List[Tag]) -> bytes:
    """ Serialize an NBT tree and return uncompressed bytes
    """
    data = b''
    for tag in nbt_tree:
        data += tag.serialize()
    return data


def extract_serialized_bytes(filename: str) -> bytes:
    """ Return uncompressed serialized NBT
    """
    with open(filename, 'rb') as nbt_file:
        file_data = nbt_file.read()

    # The file may or may not be compressed. Check for the magic number to know!
    # https://www.onicos.com/staff/iz/formats/gzip.html
    if file_data[0:2] == b'\x1f\x8b':
        import gzip
        decompressed_data: bytes = gzip.decompress(file_data)
        return decompressed_data

    return file_data


def deserialize_file(filename: str) -> List[Tag]:
    """ Deserialize a GZip compressed or uncompressed NBT file
    """
    serialized_nbt_data = extract_serialized_bytes(filename)
    return deserialize(serialized_nbt_data)


def serialize_file(filename: str, nbt_tree: List[Tag], compress: bool = True):
    """ Serialize an NBT tree, optionally compress the output, and to a file
    """
    data: bytes = serialize(nbt_tree)
    if compress:
        import gzip
        data = gzip.compress(data)
    with open(filename, 'wb') as f:
        f.write(data)
