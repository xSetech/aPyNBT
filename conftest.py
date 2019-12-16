# -*- coding: utf-8 -*-
""" pytest configuration
"""

from pathlib import Path
import random
from typing import List, Tuple

# Search for files starting in this directory:
DEFAULT_TEST_DATA_PATH = Path("test_data/")

# Consider files with these extensions to contain NBT data (compressed or uncompressed):
NBT_FILE_SUFFIXES: Tuple[str] = (
    ".dat",
)

# These files will be ignored:
DEFINTELY_NOT_NBT_BLACKLIST: Tuple[str] = (
    "uid.dat",  # Undocumented. Maybe related to Realms?
                # https://www.minecraftforum.net/forums/minecraft-java-edition/suggestions/79149-world-uid-for-multi-world-servers
)


def _find_all_test_data(root: Path = DEFAULT_TEST_DATA_PATH) -> List[Path]:
    """ Returns all testable NBT files
    """
    nbt_files = []
    for f in root.iterdir():
        if f.is_dir():
            nbt_files.extend(_find_all_test_data(f))
            continue
        if f.is_file():
            if any([f.name.endswith(suffix) for suffix in NBT_FILE_SUFFIXES]):
                if f.name not in DEFINTELY_NOT_NBT_BLACKLIST:
                    nbt_files.append(f)
                    continue

    if root is DEFAULT_TEST_DATA_PATH:
        random.shuffle(nbt_files)

    return nbt_files


FILEPATH_FILES: List[Path] = _find_all_test_data()
FILEPATH_IDS: List[str] = [str(filepath) for filepath in FILEPATH_FILES]


def pytest_addoption(parser):
    parser.addoption("--shuffle-files", action="store_true", dest="shuffle-files", help="Shuffle lists of files")
    parser.addoption("--repeat-files", action="store", type=int, default=1, dest="repeat-files", help="Number of times to test all files")


def pytest_configure(config):
    global FILEPATH_FILES, FILEPATH_IDS

    # --shuffle-files
    # --repeat-files
    if config.getoption("repeat-files") > 0:
        filepath_files = []
        filepath_ids = []
        for _ in range(config.getoption("repeat-files")):
            # Ruin the natural ordering and locality from directory traversal.
            # Similar files (such as player data) will trigger the same code paths
            # which get optimized easily by modern* CPUs.
            #
            # * Modern meaning most x86_64; definitely not all RISC variants...
            if config.getoption("shuffle-files"):
                random.shuffle(FILEPATH_FILES)
                FILEPATH_IDS = [str(filepath) for filepath in FILEPATH_FILES]
            filepath_files.extend(FILEPATH_FILES)
            filepath_ids.extend(FILEPATH_IDS)
        FILEPATH_FILES = filepath_files
        FILEPATH_IDS = filepath_ids


def pytest_generate_tests(metafunc):
    if "filepath" in metafunc.fixturenames:
        metafunc.parametrize("filepath", FILEPATH_FILES, ids=FILEPATH_IDS)

