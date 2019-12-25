# -*- coding: utf-8 -*-
""" Region/Anvil Serializer and Deserializer

https://minecraft.gamepedia.com/Region_file_format
https://minecraft.gamepedia.com/Anvil_file_format
"""

from collections import defaultdict
# import datetime
import gzip
import re
from struct import unpack
from typing import List, Optional, Tuple
import zlib

from chunk import Chunk
import nbt

re_coords_from_filename = re.compile(r"r\.([-0-9]+)\.([-0-9]+)\.mc[ar]")

def coords_from_filename(filename: str, rgx=re_coords_from_filename) -> Tuple[int, int]:
    x, z = rgx.findall(filename)[0]
    return int(x), int(z)


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
        # chunks[x][z] -> Chunk or None
        #
        # The coordinates here are the 2-d chunk offset from the top-left of the
        # region. In other words, the chunk's actual coordinates don't matter
        # here. For example, a chunk with coordinate (30, -1) cooresponds to
        # Region(x=0, z=-1).chunks[30][31].
        self.chunks: Dict[int, Dict[int, Optional[Chunk]]] = defaultdict(lambda: defaultdict(lambda: None))

        if basename is not None:
            self.x, self.z = coords_from_filename(basename)
        else:
            self.x = x
            self.z = z

        if region_data is not None:
            self.deserialize(region_data, x, z)

    def deserialize_chunk(self, region_data: memoryview, x: int, z: int):
        offset_offset = (32 * z) + (4 * x)
        timestamp_offset = offset_offset + (4 * 1024)

        # offset (3B) and sector count (1B, ignored)
        offset_bytes = region_data[offset_offset:offset_offset + 3]
        offset = int.from_bytes(offset_bytes, byteorder='big', signed=False)
        sectors = region_data[offset_offset + 3:offset_offset + 4][0]

        if offset == 0 and sectors == 0:
            return  # ungenerated chunk

        # timestamp (4B)
        #   What timezone?... Also, 2038 problem...
        #
        # timestamp_int = unpack("!I", region_data[timestamp_offset:timestamp_offset + 4])[0]
        # timestamp = datetime.datetime.fromtimestamp(timestamp_int)
        chunk_offset = 4 * 1024 * offset  # from start of file, according to the docs
        chunk_size_bytes = region_data[chunk_offset:chunk_offset + 4]
        chunk_size: int = unpack("!I", chunk_size_bytes)[0]
        compression: int = region_data[chunk_offset + 4:chunk_offset + 5][0]

        # Decompression and deserialization
        decompressed_chunk_data: bytes = None
        if compression == 1:
            decompressed_chunk_data = gzip.decompress(region_data[chunk_offset + 5:chunk_offset + 5 + chunk_size])
        elif compression == 2:
            decompressed_chunk_data = zlib.decompress(region_data[chunk_offset + 5:chunk_offset + 5 + chunk_size])

        self.chunks[x][z] = nbt.deserialize(memoryview(decompressed_chunk_data))


    def deserialize(self, region_data: memoryview, x: int, z: int):
        """ Find and deserialize all chunks stored in the region

        x & z here correspond to the location of the region as provided in the
        filename. Further down, x & z refer to the chunk offset.
        """
        # Metadata is stored in two x-major matrixes. If both fields
        # are zero, the chunk does not exist in the region (ungenerated).
        for _z in range(0, 32):
            for _x in range(0, 32):
                self.deserialize_chunk(region_data, _x, _z)

def deserialize_file(filename: str) -> Region:
    with open(filename, 'rb') as f:
        region_data = f.read()
    return Region(region_data=region_data)
