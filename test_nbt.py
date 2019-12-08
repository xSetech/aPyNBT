# -*- coding: utf-8 -*-
""" Tests for nbt.py
"""

import gzip

import pytest

import nbt


def test_deserialize_reference():
    """ Deserialization of the reference files should not fail
    """
    nbt.deserialize_file("level.dat.gz")


def test_reserialize_reference():
    """ Deserialize a file and then reserialize the data
    """
    tree = nbt.deserialize_file("level.dat.gz")
    data = nbt.serialize(tree)


def test_reserialize_reference_compared():
    """
    Same as test_reserialize_reference(), but compare the original uncompressed
        bytes to the output of the serializer. There should be no difference.
    """
    with open("level.dat.gz", "rb") as compressed_nbt_file:
        compressed_data = compressed_nbt_file.read()

    # These are the bytes that the Minecraft client/server created.
    original_data = gzip.decompress(compressed_data)
    tree = nbt.deserialize(original_data)
    data = nbt.serialize(tree)

    assert data == original_data


def test_tag_end():
    """ Test TAG_End
    """
    # No parameters are required to instantiate TAG_End since it's a special
    # case: just a zero byte.
    nbt.TAG_End().serialize() == b'\x00'
    nbt.TAG_End().size == 1


@pytest.mark.parametrize(
    "tag_class",
    [tag_class for tag_class in nbt.TAGS if tag_class in nbt.TagInt.__subclasses__()]
)
def test_tagint_serialization_lengths(tag_class):
    """
    Confirm TagInt's shared serialization method preserves the type width
    """
    tag = tag_class(name="", payload=9)  # 9 is a random value
    assert len(tag.serialize()) == 1 + 2 + tag.width  # 4

    tag = tag_class(name="", payload=9, tagged=False)
    assert len(tag.serialize()) == 0 + 2 + tag.width  # 3

    tag = tag_class(payload=9, named=False)
    assert len(tag.serialize()) == 1 + 0 + tag.width  # 2

    tag = tag_class(name="named tag", payload=9, named=True, tagged=False)
    assert len(tag.serialize()) > 1 + 2 + tag.width   # at least


@pytest.mark.parametrize(
    "tag",
    [tag_class(name=name, payload=42, named=(not not name), tagged=tagged)
        for tag_class in nbt.TAGS if tag_class in nbt.TagInt.__subclasses__()
        for name in ("", "named tag")
        for tagged in (True, False)
    ]
)
def test_tagint_payload_serialization(tag):
    for i in range(-10, 10):
        tag.payload = i                     # property setter test
        assert tag.payload == i             # property getter test
        tag.deserialize(tag.serialize())    # assert reserialization doesnt mutate the payload value
        assert tag.payload == i


def test_tag_byte_payload_validation():
    tag = nbt.TAG_Byte(named=False, tagged=False)

    # Signed bytes are somewhere around the range [-128, 128]. First assert
    # that a value well within that range is accepted by the setter, then
    # assert that a value well outside that range is rejected by the setter.
    tag.payload = 100
    assert tag.payload == 100
    tag.validate()

    with pytest.raises(OverflowError):
        tag.payload = 1000000
        assert tag.payload == 1000000
        tag.validate()

    # The payload must be of type `int`
    with pytest.raises(AssertionError):
        tag.payload = "abc"
        tag.validate()


def test_tag_float():
    pass  # TODO


def test_tag_double():
    pass  # TODO


def test_tag_byte_array_payload_validation():
    # Initialize a tag with an empty list and it's valid
    tag = nbt.TAG_Byte_Array(payload=[], named=False, tagged=False)
    assert not tag.payload
    tag.validate()

    # A non-empty list of bytes is valid
    tag.payload.append(b'\x00')
    tag.validate()

    # The payload must be a list of bytes
    with pytest.raises(AssertionError):
        tag.payload = "abc"
        tag.validate()

    # Each element of the list must be of type "bytes"
    with pytest.raises(AssertionError):
        tag.payload = [123]
        tag.validate()

    # Each element of the list must be one byte large
    with pytest.raises(AssertionError):
        tag.payload = [b'\xff\xff']
        tag.validate()


@pytest.mark.parametrize(
    "string_val",
    [
        "",     # empty string
        "a",    # single character
        "abc",  # multiple characters

        # all keyboard characters rolled into one string
        "".join([chr(i) for i in range(32, 127)]),

        "™",    # single non-ASCII character

        # multiple non-ASCII characters
        "単体テストを書く",
    ]
)
def test_tag_string(string_val):
    """ TAG_String
    """
    # Instantiate a TAG_String with a payload of "string_val". Assert that the
    # payload value was set correctly.
    tag = nbt.TAG_String(payload=string_val, named=False, tagged=False)
    assert tag.payload == string_val

    # Serialize the previous tag and pass the resuting bytes to the constructor
    # of a new tag. This tests whether we can both correctly serialize and then
    # deserialize string values.
    tag2 = nbt.TAG_String(nbt_data=tag.serialize(), named=False, tagged=False)
    assert tag2.payload == string_val


def test_tag_list():
    list_of_tag_strings = [
        nbt.TAG_String(payload=string_val, named=False, tagged=False)
        for string_val in [
            "abc",
            "defghi",
            "jkl",
        ]
    ]

    # Initialize a TAG_List with an element type of TAG_String, and validate
    # that an empty list is a valid payload.
    tag = nbt.TAG_List(
        payload=[],
        named=False,
        tagged=False,
        tagID=list_of_tag_strings[0].tid
    )
    tag.validate()

    # A list of unnamed & untagged TAG_String instances is valid.
    tag.payload = list_of_tag_strings
    tag.validate()

    # A tag that is named makes the payload invalid.
    tag.payload[0].named = True
    with pytest.raises(AssertionError):
        tag.validate()

    # A tag that is tagged makes the payload invalid.
    tag.payload[0].named = False
    tag.payload[0].tagged = True
    with pytest.raises(AssertionError):
        tag.validate()


def test_tag_compound():
    tag_end = nbt.TAG_End()

    # Initialize an empty TAG_Compound list
    tag = nbt.TAG_Compound(payload=[tag_end], named=False, tagged=False)
    tag.validate()

    # Add an element and validate
    tag_string = nbt.TAG_String(name="an example string", payload="with an example payload")
    tag.payload = [tag_string, tag_end]
    tag.validate()

    # A TAG_End is required at the end of the list
    tag.payload = [tag_string]
    with pytest.raises(AssertionError):
        tag.validate()
