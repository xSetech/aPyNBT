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

from struct import iter_unpack, pack, unpack
from typing import Any, Dict, List, Tuple


class Tag:
    """ Base class of all tags """

    # Memory and performance optimization: Declare the mutable instance
    # attributes ahead-of-time.
    __slots__ = (
        "name", "payload",
        "_size", "_tagged", "_named"
    )

    # "tag id", an immutable attribute of a specific subclass of Tag
    tid: int = None

    # Is the tag's payload an equivalent basic Python type (int, str, etc)?
    # This is a class attribute that permits significant performance gains
    # during serialization or deserialization.
    _is_primitive: bool = False

    def __init__(self, nbt_data: memoryview = None, name: str = None, payload: Any = None, named: bool = None, tagged: bool = True):
        """ Instantiation for all decedent tag types

        The purpose of this method is to populate the three tag attributes (id,
        name, and payload). Additional attributes are set for programmer
        convenience. The "name" and "payload" attributes are populated based on
        data in the byte array "nbt_data".

        Args:

            tagID::int
                The numeric identifier of the tag that's used as a key into
                TAG_TYPES to get the specific tag class.

            nbt_data::memoryview
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
        # "name" and "payload" are mutable instance attributes collected either
        # by deserialization of nbt data or by having them passed as arguments
        # to the constructor.
        self.name: str = None
        self.payload: Any = None

        # The number of bytes processed during deserialization. If the value is
        # zero, no deserialization has occurred.
        self._size: int = 0

        # Indicates the tag has bytes for its tag id.
        self._tagged: bool = tagged

        # Indicates the tag has bytes for its name.
        #
        # This constructor is optimized for deserialization. The case of
        # nbt_data being None is not the common case. As a result, note the same
        # conditional is resolved (`named is None`) lower down.
        if named is not None:
            self._named: bool = named
        else:
            self._named: bool = True

        if nbt_data is not None:
            self.deserialize(nbt_data)
        else:
            self.payload = payload

            # Inferred false _named attribute.
            if named is None and name is None:
                self._named = False
                return
            if named is False:
                return
            if name:
                self.name = name
            else:
                self.name = ""

    def deserialize(self, data: memoryview):
        """
        Deserialize a blob of data and set the `name` and `payload` attributes
            of the tag.
        """
        offset = 0

        # Tags in lists don't have a tag id byte.
        if self._tagged:
            offset = 1  # 1 byte processed (tag id)

        # Tags in lists don't have a name.
        if self._named:
            offset += self.deserialize_name(data[offset:])
        else:
            self.name = ""

        # Reminder: Payload parsing may recurse!
        offset += self.deserialize_payload(data[offset:])
        self._size = offset

    def deserialize_name(self, data: memoryview,
            _unpack=unpack,
            _memview_to_bytes=memoryview.tobytes,
            _bytes_decode=bytes.decode) -> int:
        """ Sets the `name` attribute

        The constructor is a mess because this method is called *very*
            frequently and must be optimized to avoid attribute lookups for
            `unpack`, `memoryview`, and `bytes`.
        """
        string_size = _unpack("!H", data[:2])[0]
        width = 2 + string_size
        self.name = _bytes_decode(_memview_to_bytes(data[2:width]))
        return width

    def deserialize_payload(self, data: memoryview) -> int:
        """ Sets the `payload` attribute

        This is specific to each tag and implemented in the respective tag class.
        """
        raise NotImplementedError

    @classmethod
    def deserialize_primitive(cls, data: memoryview) -> Tuple[Any, int]:
        """
        If the tag's payload can be represented as a basic Python type, a
            subclass of Tag implements this method. Passed bytes are converted to
            the tag's payload's type. The value is returned along with the number
            of bytes deserialized ("width").
        """
        raise NotImplementedError

    def serialize(self) -> bytes:
        """ Returns this tag's representation in bytes
        """
        # Special-case: TAG_End is defined as 0x00
        if isinstance(self, TAG_End):
            return b"\x00"

        # Can't serialize a base-class!
        assert self.tid is not None

        # The tag needs to at least have been initialized!
        assert self._named is not None
        assert self._tagged is not None

        data = b''
        data += self.serialize_tid()
        data += self.serialize_name()
        data += self.serialize_payload()
        return data

    def serialize_tid(self) -> bytes:
        """ Convert the tag's id into its representation in bytes
        """
        if not self._tagged:
            return b''
        return self.tid.to_bytes(1, byteorder='big', signed=False)

    def serialize_name(self) -> bytes:
        """ Convert the tag's name into its representation in bytes

        The tag name is one or two parts. The first part is two bytes
            representing the length of the string, and then second is the
            actual bytes of the string (utf-8 encoded).
        """
        if not self._named:
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

    @classmethod
    def serialize_primitive(cls, value: Any) -> bytes:
        """ The reverse of Tag.deserialize_primitive()
        """
        raise NotImplementedError

    def validate(self):
        """ Validate the current tag's payload

        No return value; an exception is raised if validation fails.
        Implementation is specific to each tag and implemented in the
        respective tag class.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        """ See https://docs.python.org/3.6/reference/datamodel.html#object.__repr__
        """
        return f"<{self.__class__} size={self._size} name='{self.name}' named={self._named} tagged={self._tagged}>"


class TAG_End(Tag):
    """ Special-case; it's basically a NULL-terminator """

    __slots__ = tuple()

    tid: int = 0x00

    _size: int = 1

    def __init__(self, *args, **kwargs):
        self.name = None
        self.payload = None
        self._named = False
        self._tagged = True


class TagInt(Tag):
    """ Parent-class for tags with an integer-typed payload
    """

    __slots__ = tuple()

    width: int = None

    _is_primitive: bool = True

    @classmethod
    def deserialize_primitive(cls, data: memoryview) -> Tuple[int, int]:
        value = int.from_bytes(
            data[:cls.width],
            byteorder='big',
            signed=True
        )
        return value, cls.width

    @classmethod
    def serialize_primitive(cls, value: int) -> bytes:
        return value.to_bytes(cls.width, byteorder='big', signed=True)

    def deserialize_payload(self, data: memoryview) -> int:
        self.payload, width = self.deserialize_primitive(data)
        return width

    def serialize_payload(self) -> bytes:
        return self.serialize_primitive(self.payload)

    def validate(self):
        assert isinstance(self.payload, int)
        self.payload.to_bytes(self.width, byteorder='big', signed=True)


class TAG_Byte(TagInt):

    __slots__ = tuple()

    tid: int = 0x01
    width: int = 1


class TAG_Short(TagInt):

    __slots__ = tuple()

    tid: int = 0x02
    width: int = 2


class TAG_Int(TagInt):

    __slots__ = tuple()

    tid: int = 0x03
    width: int = 4


class TAG_Long(TagInt):

    __slots__ = tuple()

    tid: int = 0x04
    width: int = 8


class TagFloat(Tag):
    """ Parent class for floating point tag types
    """

    __slots__ = tuple()

    _is_primitive: bool = True

    @classmethod
    def deserialize_primitive(cls, data: memoryview) -> Tuple[float, int]:
        value: float = unpack(cls.sformat, data[:cls.width])[0]
        return value, cls.width

    @classmethod
    def serialize_primitive(cls, value: float) -> bytes:
        return pack(cls.sformat, value)

    def deserialize_payload(self, data: memoryview) -> int:
        self.payload, width = self.deserialize_primitive(data)
        return width

    def serialize_payload(self) -> bytes:
        return self.serialize_primitive(self.payload)

    def validate(self):
        assert isinstance(self.payload, float)


class TAG_Float(TagFloat):

    __slots__ = tuple()

    tid: int = 0x05
    width: int = 4
    sformat: str = "!f"


class TAG_Double(TagFloat):

    __slots__ = tuple()

    tid: int = 0x06
    width: int = 8
    sformat: str = "!d"


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

    __slots__ = tuple()

    # Number of bytes that represent the number of elements in the iterable (if
    # a length field is provided by the tag at all, e.g. TAG_Compound uses
    # TAG_End to denote the end of its array).
    array_size_width: int = None


class TAG_Byte_Array(TagIterable):

    __slots__ = tuple()

    tid: int = 0x07
    array_size_width = 4  # int
    width: int = 1

    def deserialize_payload(self, data: memoryview, _unpack=unpack) -> int:
        array_size: int = _unpack("!I", data[:4])[0]
        self.payload: bytearray = bytearray(data[4:4 + array_size])
        return 4 + array_size

    def serialize_payload(self) -> bytes:
        data: bytes = len(self.payload).to_bytes(self.array_size_width, byteorder='big', signed=False)
        data += bytes(self.payload)
        return data

    def validate(self):
        assert isinstance(self.payload, bytearray)


class TAG_String(Tag):

    __slots__ = tuple()

    tid: int = 0x08
    string_size_width: int = 2  # short

    _is_primitive: bool = True

    @classmethod
    def deserialize_primitive(cls, data: memoryview, _unpack=unpack) -> Tuple[int, int]:
        string_size = _unpack("!H", data[:2])[0]

        if string_size == 0:
            return "", cls.string_size_width

        string_width = 2 + string_size
        string_value = data[2:string_width].tobytes().decode('utf-8')
        return string_value, string_width

    @classmethod
    def serialize_primitive(cls, value: str) -> bytes:
        data = b''
        encoded_string: bytes = value.encode('utf-8')
        data += len(encoded_string).to_bytes(
            cls.string_size_width,
            byteorder='big',
            signed=False
        )
        data += encoded_string
        return data

    def deserialize_payload(self, data: memoryview) -> int:
        self.payload, payload_width = self.deserialize_primitive(data[self._size:])
        return payload_width

    def serialize_payload(self) -> bytes:
        return self.serialize_primitive(self.payload)

    def validate(self):
        assert isinstance(self.payload, str)


class TAG_List(TagIterable):

    __slots__ = ("tagID",)

    tid: int = 0x09
    array_size_width: int = 4  # int

    def __init__(self, *args, tagID: int = None, **kwargs,):
        """
        The "tagID" attribute (as its called in the spec) is unique to
            TAG_List. The value gives the type of the tags stored in the payload.
            An empty Python list drops this information (which could be recovered
            by otherwise looking at the first element of the list).

        self.serialize() will fail with an AssertionError if this attribute is
            not set and the payload is an empty list!
        """
        self.tagID: int = tagID
        super(TAG_List, self).__init__(*args, **kwargs)

    def deserialize_payload(self, data: memoryview, _unpack=unpack) -> int:
        self.payload = []

        # Determine the tag type; this only gives us the class to instantiate
        tag_id = data[:1][0]
        self.tagID = tag_id  # save for serialization

        # Determine the eventual number of elements in the list
        array_size = _unpack("!I", data[1:5])[0]

        # Optimization: Don't store a list of Tag instances.
        #
        # Some unnamed, untagged "tag"s are better represented as simply a
        # basic Python type (TagNumeric -> int, TAG_String -> str, etc). We
        # don't lose any information at serialization since the tag-type is
        # known from the tagID attribute value. Supporting tag types have a
        # positive boolean attribute named "_is_primitive" and define a
        # class method for converting bytes into the corresponding Python
        # basic type. This improves performance by avoiding object
        # instantiation.
        #
        # The only tags that aren't "primitive" are usually iterables. For
        # example, TAG_List can't be represented using just a Python list
        # type because then information about what type the list is made of
        # is lost if the list is empty.
        #
        # Note on the size of each tag: They're not known ahead of time. All we
        # know is that we need to append `array_size` tags to the list.
        # Successive offsets into the data are determined by the sum of the
        # sizes of the previously deserialized tags.
        offset = 1 + self.array_size_width
        tag_type = TAG_TYPES[tag_id]
        if tag_type._is_primitive:
            for _ in range(array_size):
                value, width = tag_type.deserialize_primitive(data[offset:])
                self.payload.append(value)
                offset += width
        else:
            for _ in range(array_size):
                tag = tag_type(data[offset:], named=False, tagged=False)
                self.payload.append(tag)
                offset += tag._size
        return offset

    def serialize_payload(self) -> bytes:
        # See the docstring for TAG_List's constructor.
        assert self.tagID is not None or self.payload is not None

        # self.tagID will not have been set if deserialization was skipped. We
        #   can recover it by looking at the first element of the list.
        if self.tagID is None:
            self.tagID = self.payload[0].tid

        # Serializing the tag type and the number of them is straight-forward.
        data = b''
        data += self.tagID.to_bytes(1, byteorder='big', signed=False)
        data += len(self.payload).to_bytes(self.array_size_width, byteorder='big', signed=False)

        # If the list is empty, there's nothing to serialize :)
        if not self.payload:
            return data

        # The list has stuff in it. The stuff could be an instance of Tag, or
        # could be primitives (integers, strings, etc).
        if TAG_TYPES[self.tagID]._is_primitive:
            for primitive in self.payload:
                data += TAG_TYPES[self.tagID].serialize_primitive(primitive)
        else:
            for tag in self.payload:
                data += tag.serialize()

        return data

    def validate(self):
        assert isinstance(self.payload, list)
        for value in self.payload:
            if not TAG_TYPES[self.tagID]._is_primitive:
                assert value.__class__ in TAGS
                assert not value._named
                assert not value._tagged


class TAG_Compound(TagIterable):

    __slots__ = tuple()

    tid: int = 0x0a

    def deserialize_payload(self, data: memoryview) -> int:
        self.payload = []
        offset = 0
        while True:
            tag_id = data[offset:][0]
            tag = TAG_TYPES[tag_id](data[offset:])
            offset += tag._size
            self.payload.append(tag)
            if isinstance(tag, TAG_End):
                break
        return offset

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

    __slots__ = tuple()

    array_size_width: int = 4  # int
    width: int = None

    def deserialize_payload(self, data: memoryview, _unpack=unpack, _iter_unpack=iter_unpack) -> int:
        sformat, width = self.sformat, self.width
        array_size = _unpack("!I", data[:4])[0]
        last_index = width * array_size
        self.payload = [i[0] for i in _iter_unpack(sformat, data[4:4 + last_index])]
        return 4 + last_index

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

    __slots__ = tuple()

    tid: int = 0x0b
    width: int = 4  # int
    sformat = "!i"


class TAG_Long_Array(TagIterableNumeric):

    __slots__ = tuple()

    tid: int = 0x0c
    width: int = 8  # long
    sformat = "!q"


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


def deserialize(nbt_data: memoryview) -> List[Tag]:
    """ Deserialize NBT data and return a tree
    """
    nbt_data = memoryview(nbt_data)  # permit nbt_data to be `bytes`; noop if memoryview
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
