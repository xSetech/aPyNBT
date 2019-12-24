# -*- coding: utf-8 -*-
""" Region/Anvil Serializer and Deserializer

https://minecraft.gamepedia.com/Region_file_format
https://minecraft.gamepedia.com/Anvil_file_format
"""

from collections import defaultdict
import re
from typing import List

from chunk import Chunk

re_coords_from_filename = re.compile(r"r\.([-0-9]+)\.([-0-9]+)\.mcr")


class Region:

    __slots__ = ("x", "z", "chunks")

    def __init__(self, region_data: memoryview, basename: str = None, x: int = None, z: int = None):
        """ Instantiate a McRegion

        Regions contain 32x32 chunks.

        Args:

            region_data::bytes
                Data that contains chunks according to the McRegion file format.

            basename::str
                The optional name of the region file. This contains the region coordinates.
                Alternatively, they can be passed directly via "x" and "y".

            x::int
            z::int
                The optional region coordinates.
        """
        self.chunks: Dict[int, Dict[int, Chunk]] = defaultdict(lambda: None)

        if basename is not None:
            x, z = re_coords_from_filename.findall(basename)[0]
            self.x: int = int(x)
            self.z: int = int(z)
        else:
            self.x = x
            self.z = z

        if region_data is not None:
            self.deserialize(region_data, x, z)

    def deserialize(self, region_data: memoryview, x: int, z: int):
        # Regions contain 32x32 chunks.
        pass  # TODO


def deserialize_file(filename: str) -> Region:
    with open(filename, 'rb') as f:
        region_data = f.read()
    return Region(region_data=region_data)
