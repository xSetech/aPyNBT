# -*- coding: utf-8 -*-
""" Tests for nbt.py
"""

from pathlib import Path

import pytest

import aPyNBT.nbt as nbt


@pytest.mark.skip("only used for profiling")
def test_deserialize_all_test_data(nbt_filepath: Path):
    nbt.deserialize_file(nbt_filepath)


@pytest.mark.skip("only used for profiling")
def test_reserialize_all_test_data(nbt_filepath: Path):
    tree = nbt.deserialize_file(nbt_filepath)
    nbt.serialize(tree)


def test_reserialize_reference_compared(nbt_filepath: Path):
    """
    Same as test_reserialize_reference(), but compare the original bytes to the
    output of the serializer. There should be no difference.
    """
    orig = nbt.extract_serialized_bytes(nbt_filepath)
    tree = nbt.deserialize_file(nbt_filepath)
    data = nbt.serialize(tree)
    assert data == orig


def test_tag_named_attr():
    """ Confirm the documented behavior of the "named" parameter
    """
    # Unnamed tags don't have their None-valued "name" attribute automatically
    # converted to empty-string. The default value is None.
    unnamed_tag1 = nbt.TAG_Byte(payload=0)
    unnamed_tag2 = nbt.TAG_Byte(payload=0, named=False)
    assert unnamed_tag1.name is None and unnamed_tag2.name is None
    assert unnamed_tag1.serialize() == unnamed_tag2.serialize()
    assert unnamed_tag1.name is None and unnamed_tag2.name is None

    # Named tags behave differently. The name attribute is converted to
    # empty-string automatically in the constructor and during serialization.
    named_tag1 = nbt.TAG_Byte(payload=0, named=True)
    named_tag2 = nbt.TAG_Byte(payload=0, named=True, name=None)
    assert named_tag1.name == "" and named_tag2.name == ""
    assert named_tag1.serialize() == named_tag2.serialize()
    assert named_tag1.name == "" and named_tag2.name == ""

    named_tag3 = nbt.TAG_Byte(payload=0, named=True)
    named_tag3.name = None
    assert named_tag3.name is None
    assert named_tag3.serialize() == named_tag1.serialize()
    assert named_tag3.name == ""

    # Double-check that a non-empty non-None value for a name stays that way...
    # and that the named attribute is correctly inferred.
    named_tag_with_name = nbt.TAG_Byte(payload=0, name="a tag name test")
    assert named_tag_with_name._named
    assert named_tag_with_name.name == "a tag name test"
    named_tag_with_name.serialize()
    assert named_tag_with_name.name == "a tag name test"

    # More checks that that the named attribute is correctly inferred.
    tag_from_deserialization1 = nbt.TAG_Byte(nbt_data=memoryview(named_tag_with_name.serialize()))
    assert tag_from_deserialization1._named is True
    assert tag_from_deserialization1.payload == 0
    assert tag_from_deserialization1.name == "a tag name test"
    assert tag_from_deserialization1.serialize() == named_tag_with_name.serialize()

    tag_from_deserialization2 = nbt.TAG_Byte(nbt_data=memoryview(unnamed_tag1.serialize()), named=False)
    assert tag_from_deserialization2._named is False


def test_tag_end():
    """ Test TAG_End
    """
    # No parameters are required to instantiate TAG_End since it's a special
    # case: just a zero byte.
    nbt.TAG_End().serialize() == b'\x00'
    nbt.TAG_End()._size == 1


@pytest.mark.parametrize(
    "tag_instance",
    [
        nbt.TAG_End(payload=None, name="tag repr test"),
        nbt.TAG_Byte(payload=1, name="tag repr test"),
        nbt.TAG_Short(payload=1, name="tag repr test"),
        nbt.TAG_Int(payload=1, name="tag repr test"),
        nbt.TAG_Long(payload=1, name="tag repr test"),
        nbt.TAG_Float(payload=1.0, name="tag repr test"),
        nbt.TAG_Double(payload=1.0, name="tag repr test"),
        nbt.TAG_Byte_Array(payload=[b'\x00', b'\x01'], name="tag repr test"),
        nbt.TAG_String(payload="string repr test", name="tag repr test"),
        nbt.TAG_List(payload=["tag list repr test"], name="tag repr test", tagID=nbt.TAG_String.tid),
        nbt.TAG_Compound(payload=[nbt.TAG_End()], name="tag repr test"),
        nbt.TAG_Int_Array(payload=[1, 2, 3], name="tag repr test"),
        nbt.TAG_Long_Array(payload=[1, 2, 3], name="tag repr test"),
    ],
    ids=[
        "nbt.TAG_End",
        "nbt.TAG_Byte",
        "nbt.TAG_Short",
        "nbt.TAG_Int",
        "nbt.TAG_Long",
        "nbt.TAG_Float",
        "nbt.TAG_Double",
        "nbt.TAG_Byte_Array",
        "nbt.TAG_String",
        "nbt.TAG_List",
        "nbt.TAG_Compound",
        "nbt.TAG_Int_Array",
        "nbt.TAG_Long_Array",
    ]
)
def test_repr(tag_instance):
    """ Test each Tag's __repr__
    """
    str(tag_instance)


@pytest.mark.parametrize(
    "tag_class",
    [tag_class for tag_class in nbt.TAGS if tag_class in nbt.TagInt.__subclasses__()]
)
def test_tagint_serialization_lengths(tag_class):
    """
    Confirm TagInt's shared serialization method preserves the type width
    """
    tag = tag_class(name="", payload=9)  # 9 is a random value
    assert len(tag.serialize()) == 1 + 2 + tag.width  # 4

    tag = tag_class(name="", payload=9, tagged=False)
    assert len(tag.serialize()) == 0 + 2 + tag.width  # 3

    tag = tag_class(payload=9)
    assert len(tag.serialize()) == 1 + 0 + tag.width  # 2

    tag = tag_class(name="named tag", payload=9, named=True, tagged=False)
    assert len(tag.serialize()) > 1 + 2 + tag.width   # at least


@pytest.mark.parametrize(
    "tag",
    [
        tag_class(name=name, payload=42, named=(not not name), tagged=tagged)
        for tag_class in nbt.TAGS if tag_class in nbt.TagInt.__subclasses__()
        for name in ("", "named tag")
        for tagged in (True, False)
    ]
)
def test_tagint_payload_serialization(tag):
    for i in range(-10, 10):
        tag.payload = i                     # property setter test
        assert tag.payload == i             # property getter test
        tag.deserialize(memoryview(tag.serialize()))    # assert reserialization doesn't mutate the payload value
        assert tag.payload == i


def test_tag_byte_payload_validation():
    tag = nbt.TAG_Byte(tagged=False)

    # Signed bytes are somewhere around the range [-128, 128]. First assert
    # that a value well within that range is accepted by the setter, then
    # assert that a value well outside that range is rejected by the setter.
    tag.payload = 100
    assert tag.payload == 100
    tag.validate()

    with pytest.raises(OverflowError):
        tag.payload = 1000000
        assert tag.payload == 1000000
        tag.validate()

    # The payload must be of type `int`
    with pytest.raises(AssertionError):
        tag.payload = "abc"
        tag.validate()


def test_tag_float():
    pass  # TODO


def test_tag_double():
    pass  # TODO


def test_tag_byte_array_payload_validation():
    tag = nbt.TAG_Byte_Array(payload=bytearray(), tagged=False)
    assert not tag.payload
    tag.validate()

    # Assert a non-empty bytearray is valid
    tag.payload.append(0)  # append int
    tag.payload.extend(b'\x00')  # append byte
    assert len(tag.payload) == 2
    tag.validate()

    # The payload must be a bytearray
    with pytest.raises(AssertionError):
        tag.payload = "abc"
        tag.validate()
    with pytest.raises(AssertionError):
        tag.payload = [b'\xff\xff']
        tag.validate()
    with pytest.raises(AssertionError):
        tag.payload = [123]
        tag.validate()


@pytest.mark.parametrize(
    "string_val",
    [
        "",     # empty string
        "a",    # single character
        "abc",  # multiple characters

        # all keyboard characters rolled into one string
        "".join([chr(i) for i in range(32, 127)]),

        "™",    # single non-ASCII character

        # multiple non-ASCII characters
        "単体テストを書く",
    ]
)
def test_tag_string(string_val):
    """ TAG_String
    """
    # Instantiate a TAG_String with a payload of "string_val". Assert that the
    # payload value was set correctly.
    tag = nbt.TAG_String(payload=string_val, tagged=False)
    assert tag.payload == string_val

    # Serialize the previous tag and pass the resulting bytes to the constructor
    # of a new tag. This tests whether we can both correctly serialize and then
    # deserialize string values.
    tag2 = nbt.TAG_String(nbt_data=memoryview(tag.serialize()), named=False, tagged=False)
    assert tag2.payload == string_val


def test_tag_list_with_tags():
    """ [tag, tag, ...]
    """
    payload = [
        nbt.TAG_Int_Array(payload=[1, 2, 3, 4], tagged=False),
        nbt.TAG_Int_Array(payload=[5, 6, 7, 8], tagged=False),
    ]

    # Initialize a TAG_List with an element type of TAG_Int_Array, and validate
    # that an empty list is a valid payload.
    tag = nbt.TAG_List(
        payload=[],
        tagged=False,
        tagID=payload[0].tid
    )
    tag.validate()

    # A list of unnamed & untagged TAG_Int_Array instances is valid.
    tag.payload = payload
    tag.validate()

    # A tag that is named makes the payload invalid.
    tag.payload[0]._named = True
    with pytest.raises(AssertionError):
        tag.validate()

    # A tag that is tagged makes the payload invalid.
    tag.payload[0]._named = False
    tag.payload[0]._tagged = True
    with pytest.raises(AssertionError):
        tag.validate()


def test_tag_list_with_primitives():
    """ [str, str, ...]
    """
    payload = [
        "abc",
        "123"
    ]

    # Initialize a TAG_List with an element type of TAG_String, and validate
    # that an empty list is a valid payload.
    tag = nbt.TAG_List(
        payload=[],
        tagged=False,
        tagID=nbt.TAG_String.tid
    )
    tag.validate()

    # A list of strings is valid.
    tag.payload = payload
    tag.validate()


def test_tag_compound():
    tag_end = nbt.TAG_End()

    # Initialize an empty TAG_Compound list
    tag = nbt.TAG_Compound(payload=[tag_end], tagged=False)
    tag.validate()

    # Add an element and validate
    tag_string = nbt.TAG_String(name="an example string", payload="with an example payload")
    tag.payload = [tag_string, tag_end]
    tag.validate()

    # A TAG_End is required at the end of the list
    tag.payload = [tag_string]
    with pytest.raises(AssertionError):
        tag.validate()
