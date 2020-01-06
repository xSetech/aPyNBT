# -*- coding: utf-8 -*-
""" Region/Anvil Serializer and Deserializer

https://minecraft.gamepedia.com/Region_file_format
https://minecraft.gamepedia.com/Anvil_file_format
"""

from collections import defaultdict
# from datetime import datetime
from enum import IntEnum
import gzip
from math import ceil
import os
import re
from struct import pack, unpack
from typing import Dict, List, Optional, Tuple
import zlib

from . import nbt

re_coords_from_filename = re.compile(r"r\.([-0-9]+)\.([-0-9]+)\.mc[ar]")


def coords_from_filename(filename: str, rgx=re_coords_from_filename) -> Tuple[int, int]:
    x, z = rgx.findall(filename)[0]
    return int(x), int(z)


class Compression(IntEnum):
    GZIP = 1
    ZLIB = 2


class Region:

    __slots__ = (
        "x", "z", "chunks", "timestamps", "compression",
        "_offsets", "_sectors"
    )

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
        # here. For example, a chunk with coordinate (30, -1) corresponds to
        # Region(x=0, z=-1).chunks[30][31].
        self.chunks: Dict[int, Dict[int, Optional[List[nbt.Tag]]]] = defaultdict(lambda: defaultdict(lambda: None))
        self.timestamps: Dict[int, Dict[int, Optional[int]]] = defaultdict(lambda: defaultdict(int))
        self.compression: Dict[int, Dict[int, Optional[int]]] = defaultdict(lambda: defaultdict(lambda: None))

        # Copies of the original values; used for serialization and testing
        self._offsets: Dict[int, Dict[int, Optional[int]]] = defaultdict(lambda: defaultdict(int))
        self._sectors: Dict[int, Dict[int, Optional[int]]] = defaultdict(lambda: defaultdict(int))

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

        # chunk data offset (3 bytes) and sector count (1 byte)
        offset_bytes = region_data[metadata_offset:metadata_offset + 3]
        offset = int.from_bytes(offset_bytes, byteorder='big', signed=False)
        sectors = region_data[metadata_offset + 3:metadata_offset + 4][0]
        self._offsets[z][x] = offset
        self._sectors[z][x] = sectors

        if offset == 0 and sectors == 0:
            return  # ungenerated chunk

        # timestamp (4 bytes)
        #   What timezone?... Also, 2038 problem...
        timestamp_offset = metadata_offset + 4096  # constant 4KiB offset
        timestamp = unpack("!I", region_data[timestamp_offset:timestamp_offset + 4])[0]

        # TODO
        # chunk_last_update = datetime.fromtimestamp(timestamp)
        chunk_last_update = timestamp

        # Chunk data (4 bytes size, 2 bytes compression, n-bytes compressed data)
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
        # Metadata is stored in two x-major matrices.
        for z in range(0, 32):
            for x in range(0, 32):
                self.deserialize_chunk(region_data, x, z)

    def serialize(self) -> bytes:
        """ Return the bytes representation of this region and all contained chunks
        """
        chunk_bytes: Dict[int, Dict[int, bytearray]] = defaultdict(lambda: defaultdict(lambda: None))

        # 4 KiB sector offset to start of chunk data
        chunk_sectors_offset: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

        # Number of 4 KiB sectors spanned
        chunk_sectors_spanned: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

        # Chunk serialization and compression
        next_offset = 2  # in 4 KiB sectors
        for z in range(0, 32):
            for x in range(0, 32):
                if self.chunks[z][x] is not None:
                    chunk_sectors_offset[z][x] = next_offset
                    serialized_chunk_data: bytes = nbt.serialize(self.chunks[z][x])

                    # Compress the serialized data, reusing the reference
                    chunk_compression = Compression(self.compression[z][x])
                    if chunk_compression == Compression.ZLIB:
                        serialized_chunk_data: bytes = zlib.compress(serialized_chunk_data)
                    elif chunk_compression == Compression.GZIP:
                        serialized_chunk_data: bytes = gzip.compress(serialized_chunk_data)

                    # Compute and save the number of sectors required to store the chunk
                    chunk_size: int = 5 + len(serialized_chunk_data)
                    chunk_span: int = ceil(chunk_size / 4096)
                    next_offset += chunk_span
                    chunk_sectors_spanned[z][x]: int = chunk_span

                    # Pre-allocate the space required to store the chunk (0-filled)
                    chunk_data = bytearray(chunk_span * 4096)

                    chunk_data[:4] = pack("!I", chunk_size)
                    chunk_data[4:5] = pack("!B", chunk_compression)
                    chunk_data[5:5 + len(serialized_chunk_data)] = serialized_chunk_data

                    chunk_bytes[z][x] = chunk_data
                    assert len(chunk_bytes[z][x]) == chunk_span * 4096

        # Metadata (offsets, spans, timestamps) serialization
        metadata: bytearray = bytearray(4096)
        timestamps: bytearray = bytearray(4096)
        for z in range(0, 32):
            for x in range(0, 32):
                metadata_offset = (128 * z) + (4 * x)
                metadata[metadata_offset + 0:metadata_offset + 3] = chunk_sectors_offset[z][x].to_bytes(3, byteorder='big', signed=False)
                metadata[metadata_offset + 3:metadata_offset + 4] = pack("!B", chunk_sectors_spanned[z][x])
                timestamps[metadata_offset:metadata_offset + 4] = pack("!I", self.timestamps[z][x])

        packed_chunk_data: bytearray = bytearray()
        for z in range(0, 32):
            for x in range(0, 32):
                if chunk_bytes[z][x] is not None:
                    packed_chunk_data += chunk_bytes[z][x]

        return metadata + timestamps + packed_chunk_data


def deserialize_file(filename: str) -> Region:
    with open(filename, 'rb') as f:
        region_data = f.read()
    region_basename = os.path.basename(filename)
    r = Region(region_data=region_data, basename=region_basename)
    return r
