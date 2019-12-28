# -*- coding: utf-8 -*-
""" Region/Anvil Serializer and Deserializer

https://minecraft.gamepedia.com/Region_file_format
https://minecraft.gamepedia.com/Anvil_file_format
"""

from collections import defaultdict
from datetime import datetime
from enum import IntEnum
import gzip
import os
import re
from struct import unpack
from typing import Dict, List, Optional, Tuple
import zlib

import nbt

re_coords_from_filename = re.compile(r"r\.([-0-9]+)\.([-0-9]+)\.mc[ar]")


def coords_from_filename(filename: str, rgx=re_coords_from_filename) -> Tuple[int, int]:
    x, z = rgx.findall(filename)[0]
    return int(x), int(z)


class Compression(IntEnum):
    GZIP = 1
    ZLIB = 2


class Region:

    __slots__ = ("x", "z", "chunks", "timestamps", "compression")

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
        # chunks[z][x] -> Chunk or None
        #
        # The coordinates here are the 2-d chunk offset from the top-left of the
        # region. In other words, the chunk's actual coordinates don't matter
        # here. For example, a chunk with coordinate (30, -1) cooresponds to
        # Region(x=0, z=-1).chunks[30][31].
        self.chunks: Dict[int, Dict[int, Optional[List[nbt.Tag]]]] = defaultdict(lambda: defaultdict(lambda: None))
        self.timestamps: Dict[int, Dict[int, Optional[int]]] = defaultdict(lambda: defaultdict(int))
        self.compression: Dict[int, Dict[int, Optional[int]]] = defaultdict(lambda: defaultdict(lambda: None))

        if basename is not None:
            self.x, self.z = coords_from_filename(basename)
        else:
            self.x = x
            self.z = z

        if region_data is not None:
            self.deserialize(region_data)

    def __iter__(self):
        for z in range(0, 32):
            for x in range(0, 32):
                yield self.chunks[z][x]

    def deserialize_chunk(self, region_data: memoryview, x: int, z: int):
        """ Deserialize a chunk at offset coordinate (x, z)

        This method sets these attributes:
            self.chunks (nbt trees)
            self.timestamps (as datetime instances)
            self.compression (an enum)

        Chunk sector sizes are computed during serialization.
        """
        metadata_offset = (128 * z) + (4 * x)

        # chunk data offset (3B) and sector count (1B)
        offset_bytes = region_data[metadata_offset:metadata_offset + 3]
        offset = int.from_bytes(offset_bytes, byteorder='big', signed=False)
        sectors = region_data[metadata_offset + 3:metadata_offset + 4][0]
        self._offsets[z][x] = offset
        self._sectors[z][x] = sectors

        if offset == 0 and sectors == 0:
            return  # ungenerated chunk

        # timestamp (4B)
        #   What timezone?... Also, 2038 problem...
        timestamp_offset = metadata_offset + 4096  # constant 4KiB offset
        timestamp = unpack("!I", region_data[timestamp_offset:timestamp_offset + 4])[0]

        # TODO
        #chunk_last_update = datetime.fromtimestamp(timestamp)
        chunk_last_update = timestamp

        # Chunk data (4B size, 1B compression, nB compressed NBT data)
        chunk_offset: int = 4 * 1024 * offset  # from start of file, according to the docs
        chunk_size_bytes: memoryview = region_data[chunk_offset:chunk_offset + 4]
        chunk_size: int = unpack("!I", chunk_size_bytes)[0]
        chunk_compression: Compression = Compression(region_data[chunk_offset + 4:chunk_offset + 5][0])

        # Decompression and deserialization
        chunk_data: memoryview = region_data[chunk_offset + 5:chunk_offset + 5 + chunk_size]
        if chunk_compression == Compression.GZIP:
            chunk_data = memoryview(gzip.decompress(chunk_data))
        elif chunk_compression == Compression.ZLIB:
            chunk_data = memoryview(zlib.decompress(chunk_data))

        self.chunks[z][x] = nbt.deserialize(chunk_data)
        self.timestamps[z][x] = chunk_last_update
        self.compression[z][x] = chunk_compression

    def deserialize(self, region_data: memoryview):
        """ Find and deserialize all chunks stored in the region

        x & z here correspond to the location of the region as provided in the
        filename. Further down, x & z refer to the chunk offset.
        """
        # Metadata is stored in two x-major matrixes.
        for z in range(0, 32):
            for x in range(0, 32):
                self.deserialize_chunk(region_data, x, z)


def deserialize_file(filename: str) -> Region:
    with open(filename, 'rb') as f:
        region_data = f.read()
    return Region(region_data=region_data, basename=os.path.basename(filename))
