# -*- coding: utf-8 -*-
""" Tests for nbt.py
"""

import nbt


def test_deserialize_reference():
    """ Deserialization of the reference files should not fail
    """
    nbt.deserialize_file("level.dat.gz")


