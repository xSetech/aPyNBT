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
def test_serialization_lengths_numerics(tag_class):
    """
    Confirm TagInt's shared serialization method preserves the type width
    """
    tag = tag_class(attrs=("", 9))  # 9 is a random value
    assert len(tag.serialize()) == 1 + 2 + tag.width  # 4

    tag = tag_class(attrs=("", 9), tagged=False)
    assert len(tag.serialize()) == 0 + 2 + tag.width  # 3

    tag = tag_class(attrs=("", 9), named=False)
    assert len(tag.serialize()) == 1 + 0 + tag.width  # 2


def test_tag_byte():
    pass


def test_tag_short():
    pass


def test_tag_int():
    pass


def test_tag_long():
    pass


def test_tag_float():
    pass


def test_tag_double():
    pass


def test_tag_byte_array():
    pass


def test_tag_string():
    pass


def test_tag_list():
    pass


def test_tag_compound():
    pass


def test_tag_int_array():
    pass


def test_tag_long_array():
    pass


