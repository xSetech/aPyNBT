# aPyNBT

An implementation of a [deserializer and serializer](https://en.wikipedia.org/wiki/Serialization) for [Minecraft](https://www.minecraft.net/) binary formats, specifically [NBT](https://minecraft.gamepedia.com/NBT_format) and [Region](https://minecraft.gamepedia.com/Region_file_format)/[Anvil](https://minecraft.gamepedia.com/Anvil_file_format), written for and tested on [Python 3.6](https://docs.python.org/3.6/).

## Motivation and Focus

This project started as an experiment in understanding the Named Binary Tag (NBT) serialization format created by [Markus
Persson](https://en.wikipedia.org/wiki/Markus_Persson). It later expanded to understanding the Region/Anvil file-formats. This library is focused on quick deserialization of NBT or Region/Anvil binary into Python [data structures](https://docs.python.org/3.6/tutorial/classes.html) and [primitive types](https://docs.python.org/3.6/library/stdtypes.html). It avoids being a library for manipulating higher-level game objects (e.g. [books](https://minecraft.gamepedia.com/Book_and_Quill), [signs](https://minecraft.gamepedia.com/Sign), or [player data](https://minecraft.gamepedia.com/Player.dat_format)). There are no guarantees or checks performed by this code that confirms the Minecraft client or server will accept modified data.

## Installing

aPyNBT is available on PyPI:

```
pip install aPyNBT
```

## Releasing

Releases are done manually:

```
python3.6 setup.py sdist bdist_wheel
twine upload --repository-url https://upload.pypi.org/legacy/ dist/*
```

## nbtviewer.py

nbtviewer.py is a rough example use of the library. Pass it e.g. a [level.dat](https://minecraft.gamepedia.com/Level_format#level.dat_format):

```
TYPE                             LVL  SIZE                      NAME = VALUE
----------------------------------------------------------------------
TAG_Compound                       0  2058B                          = 2 children
  TAG_Compound                     1  2054B                     Data = 19 children
    TAG_Long                       2    21B               RandomSeed = -7724932828977041023
    TAG_String                     2    25B            generatorName = DEFAULT
    TAG_Compound                   2  1768B                   Player = 28 children
      TAG_Short                    3    15B               SleepTimer = 0
      TAG_Compound                 3    63B                abilities = 5 children
        TAG_Byte                   4    16B             invulnerable = 0
        TAG_Byte                   4    10B                   mayfly = 0
        TAG_Byte                   4    14B               instabuild = 0
        TAG_Byte                   4    10B                   flying = 0
        TAG_End                    4     1B                          =
      TAG_Float                    3    19B             FallDistance = 0.0
      TAG_Short                    3    14B                DeathTime = 0
      TAG_Int                      3    14B                  XpTotal = 0
      TAG_List                     3    38B                   Motion = 3 children of type TAG_Double
        <class 'float'>            4     8B                          = 4.9796312086493114e-55
        <class 'float'>            4     8B                          = -0.0784000015258789
        <class 'float'>            4     8B                          = -7.038076210318639e-55
      TAG_Int                      3    13B                   SpawnY = 114
      TAG_Short                    3    11B                   Health = 20
      TAG_Int                      3    13B                   SpawnZ = -456
      TAG_Float                    3    26B      foodSaturationLevel = 0.0
      TAG_Int                      3    13B                   SpawnX = 725
      TAG_Short                    3     8B                      Air = 300
      TAG_Byte                     3    12B                 OnGround = 1
      TAG_Int                      3    16B                Dimension = 0
      TAG_List                     3    24B                 Rotation = 2 children of type TAG_Float
        <class 'float'>            4     4B                          = 196.50099182128906
        <class 'float'>            4     4B                          = 3.1499271392822266
      TAG_Int                      3    14B                  XpLevel = 0
      TAG_Int                      3    12B                    Score = 0
      TAG_Byte                     3    12B                 Sleeping = 0
      TAG_List                     3    35B                      Pos = 3 children of type TAG_Double
        <class 'float'>            4     8B                          = 858.5151604084725
        <class 'float'>            4     8B                          = 89.62000000476837
        <class 'float'>            4     8B                          = -544.3398051110646
      TAG_Short                    3     9B                     Fire = -20
      TAG_Float                    3    10B                      XpP = 0.0
      TAG_Int                      3    16B                foodLevel = 12
      TAG_Float                    3    26B      foodExhaustionLevel = 2.424607753753662
      TAG_Short                    3    13B                 HurtTime = 0
      TAG_Short                    3    15B               AttackTime = 0
      TAG_List                     3  1277B                Inventory = 35 children of type TAG_Compound
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 0
          TAG_Short                5     7B                       id = 295
          TAG_Byte                 5     9B                    Count = 18
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 1
          TAG_Short                5     7B                       id = 355
          TAG_Byte                 5     9B                    Count = 1
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 2
          TAG_Short                5     7B                       id = 344
          TAG_Byte                 5     9B                    Count = 10
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 3
          TAG_Short                5     7B                       id = 360
          TAG_Byte                 5     9B                    Count = 8
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 4
          TAG_Short                5     7B                       id = 3
          TAG_Byte                 5     9B                    Count = 58
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 5
          TAG_Short                5     7B                       id = 277
          TAG_Byte                 5     9B                    Count = 1
          TAG_Short                5    11B                   Damage = 811
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 6
          TAG_Short                5     7B                       id = 279
          TAG_Byte                 5     9B                    Count = 1
          TAG_Short                5    11B                   Damage = 706
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 7
          TAG_Short                5     7B                       id = 278
          TAG_Byte                 5     9B                    Count = 1
          TAG_Short                5    11B                   Damage = 391
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 8
          TAG_Short                5     7B                       id = 366
          TAG_Byte                 5     9B                    Count = 16
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 9
          TAG_Short                5     7B                       id = 325
          TAG_Byte                 5     9B                    Count = 1
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 10
          TAG_Short                5     7B                       id = 4
          TAG_Byte                 5     9B                    Count = 64
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 11
          TAG_Short                5     7B                       id = 280
          TAG_Byte                 5     9B                    Count = 7
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 12
          TAG_Short                5     7B                       id = 365
          TAG_Byte                 5     9B                    Count = 10
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 13
          TAG_Short                5     7B                       id = 5
          TAG_Byte                 5     9B                    Count = 42
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 14
          TAG_Short                5     7B                       id = 61
          TAG_Byte                 5     9B                    Count = 3
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 15
          TAG_Short                5     7B                       id = 331
          TAG_Byte                 5     9B                    Count = 30
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 16
          TAG_Short                5     7B                       id = 65
          TAG_Byte                 5     9B                    Count = 59
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 17
          TAG_Short                5     7B                       id = 4
          TAG_Byte                 5     9B                    Count = 64
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 18
          TAG_Short                5     7B                       id = 262
          TAG_Byte                 5     9B                    Count = 2
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 20
          TAG_Short                5     7B                       id = 13
          TAG_Byte                 5     9B                    Count = 1
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 21
          TAG_Short                5     7B                       id = 58
          TAG_Byte                 5     9B                    Count = 1
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 22
          TAG_Short                5     7B                       id = 76
          TAG_Byte                 5     9B                    Count = 22
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 23
          TAG_Short                5     7B                       id = 50
          TAG_Byte                 5     9B                    Count = 23
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 24
          TAG_Short                5     7B                       id = 4
          TAG_Byte                 5     9B                    Count = 64
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 25
          TAG_Short                5     7B                       id = 326
          TAG_Byte                 5     9B                    Count = 1
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 26
          TAG_Short                5     7B                       id = 4
          TAG_Byte                 5     9B                    Count = 40
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 27
          TAG_Short                5     7B                       id = 288
          TAG_Byte                 5     9B                    Count = 57
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 28
          TAG_Short                5     7B                       id = 4
          TAG_Byte                 5     9B                    Count = 63
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 29
          TAG_Short                5     7B                       id = 325
          TAG_Byte                 5     9B                    Count = 1
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 30
          TAG_Short                5     7B                       id = 85
          TAG_Byte                 5     9B                    Count = 37
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 31
          TAG_Short                5     7B                       id = 296
          TAG_Byte                 5     9B                    Count = 2
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 32
          TAG_Short                5     7B                       id = 103
          TAG_Byte                 5     9B                    Count = 10
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 33
          TAG_Short                5     7B                       id = 263
          TAG_Byte                 5     9B                    Count = 11
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 34
          TAG_Short                5     7B                       id = 3
          TAG_Byte                 5     9B                    Count = 45
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
        TAG_Compound               4    36B                          = 5 children
          TAG_Byte                 5     8B                     Slot = 35
          TAG_Short                5     7B                       id = 69
          TAG_Byte                 5     9B                    Count = 25
          TAG_Short                5    11B                   Damage = 0
          TAG_End                  5     1B                          =
      TAG_Int                      3    20B            foodTickTimer = 0
      TAG_End                      3     1B                          =
    TAG_Int                        2    13B                   SpawnY = 64
    TAG_Int                        2    15B                 rainTime = 22432
    TAG_Int                        2    18B              thunderTime = 149982
    TAG_Int                        2    13B                   SpawnZ = 252
    TAG_Byte                       2    12B                 hardcore = 0
    TAG_Int                        2    13B                   SpawnX = 12
    TAG_Byte                       2    11B                  raining = 0
    TAG_Long                       2    15B                     Time = -7724932775668099000
    TAG_Byte                       2    14B               thundering = 0
    TAG_Int                        2    15B                 GameType = 0
    TAG_Byte                       2    15B              MapFeatures = 1
    TAG_Int                        2    14B                  version = 19132
    TAG_Long                       2    21B               LastPlayed = 1574921277333
    TAG_String                     2    22B                LevelName = valhalla
    TAG_Long                       2    21B               SizeOnDisk = 251522884
    TAG_End                        2     1B                          =
  TAG_End                          1     1B                          =
```
