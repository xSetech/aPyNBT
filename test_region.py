# -*- coding: utf-8 -*-
""" Tests for region.py
"""

import pytest

import region


def test_region_deserialization(region_filepath):
    region.deserialize_file(region_filepath)


def test_anvil_deserialization(anvil_filepath):
    """ Effectively the same as test_region_deserialization()
    """
    region.deserialize_file(anvil_filepath)

