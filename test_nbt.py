# -*- coding: utf-8 -*-
""" Tests for nbt.py
"""

import gzip

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


