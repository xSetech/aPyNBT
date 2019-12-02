# -*- coding: utf-8 -*-
""" Tests for nbt.py
"""

import gzip

import pytest

import nbt

TAG_CLASSES = [tag_class for tag_class in nbt.TAG_TYPES.values()]


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
    [tag_class for tag_class in TAG_CLASSES if tag_class in nbt.TagInt.__subclasses__()]
)
def test_tagint_serialization_lengths(tag_class):
    """
    Confirm TagInt's shared serialization method preserves the type width
    """
    tag = tag_class(attrs=("", 9))  # 9 is a random value
    assert len(tag.serialize()) == 1 + 2 + tag.width  # 4

    tag = tag_class(attrs=("", 9), tagged=False)
    assert len(tag.serialize()) == 0 + 2 + tag.width  # 3

    tag = tag_class(attrs=("", 9), named=False)
    assert len(tag.serialize()) == 1 + 0 + tag.width  # 2

    tag = tag_class(attrs=("named tag", 9), named=True, tagged=False)
    assert len(tag.serialize()) > 1 + 2 + tag.width   # at least


@pytest.mark.parametrize(
    "tag",
    [tag_class(attrs=(name, 42), named=(not not name), tagged=tagged)
        for tag_class in TAG_CLASSES if tag_class in nbt.TagInt.__subclasses__()
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


def test_tag_float():
    pass


def test_tag_double():
    pass


def test_tag_byte_array():
    pass


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
    tag = nbt.TAG_String(attrs=("", string_val), named=False, tagged=False)
    assert tag.payload == string_val

    # Serialize the previous tag and pass the resuting bytes to the constructor
    # of a new tag. This tests whether we can both correctly serialize and then
    # deserialize string values.
    tag2 = nbt.TAG_String(nbt_data=tag.serialize(), named=False, tagged=False)
    assert tag2.payload == string_val


def test_tag_list():
    pass


def test_tag_compound():
    pass


def test_tag_int_array():
    pass


def test_tag_long_array():
    pass


