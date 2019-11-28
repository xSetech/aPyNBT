""" NBT File Format Parser
2019 Seth Junot (xsetech@gmail.com)
"""

from typing import Dict


class TagType:
    pass


TAG_TYPES: Dict[int, TagType] = {
    0x00: TAG_End,
    0x01: TAG_Byte,
    0x02: TAG_Short,
    0x03: TAG_Int,
    0x04: TAG_Long,
    0x05: TAG_Float,
    0x06: TAG_Double,
    0x07: TAG_Byte_Array,
    0x08: TAG_String,
    0x09: TAG_List,
    0x0a: TAG_Compound,
    0x0b: TAG_Int_Array,
    0x0c: TAG_Long_Array
}
