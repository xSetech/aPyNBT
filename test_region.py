# -*- coding: utf-8 -*-
""" Tests for region.py
"""

import os

import pytest

import region


@pytest.mark.parametrize(
    "filename,coords",
    [
        ("r.0.0.mcr",       (0,0)),
        ("r.0.1.mcr",       (0,1)),
        ("r.0.2.mcr",       (0,2)),
        ("r.-1.0.mcr",      (-1,0)),
        ("r.-2.0.mcr",      (-2,0)),
        ("r.-3.0.mcr",      (-3,0)),
        ("r.-1.-4.mcr",     (-1,-4)),
        ("r.-2.-5.mcr",     (-2,-5)),
        ("r.-3.-6.mcr",     (-3,-6)),
        ("r.-123.123.mcr",  (-123,123)),
        ("r.123.-123.mcr",  (123,-123)),
        ("r.-123456789.-123456789.mcr",  (-123456789,-123456789)),
    ]
)
def test_coords_from_filename(filename, coords):
    # mcr
    coords_from_filename = region.coords_from_filename(filename)
    assert coords_from_filename == coords
    # mca
    filename = filename.replace("mcr", "mca")
    coords_from_filename = region.coords_from_filename(filename)
    assert coords_from_filename == coords


def test_coords_from_region_references(region_filepath):
    region.coords_from_filename(os.path.basename(region_filepath))


def test_coords_from_anvil_references(anvil_filepath):
    region.coords_from_filename(os.path.basename(anvil_filepath))


def test_region_deserialization(region_filepath):
    region.deserialize_file(region_filepath)


def test_anvil_deserialization(anvil_filepath):
    """ Effectively the same as test_region_deserialization()
    """
    region.deserialize_file(anvil_filepath)

