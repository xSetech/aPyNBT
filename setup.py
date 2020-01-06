from setuptools import setup

setup(
    name="aPyNBT",
    version="0.3a",
    packages=['aPyNBT'],
    python_requires="3.6+",
    license="GNU Lesser General Public License version 3",
    author="Seth Junot",
    author_email="xsetech@gmail.com",
    description="Deserializer and serializer for Minecraft binary formats",
    long_description="A deserializer and serializer for Minecraft binary formats, specifically NBT and Region/Anvil.",
    keywords="nbt region anvil minecraft python3",
    url="https://github.com/xSetech/aPyNBT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3 :: Only",
    ]
)
