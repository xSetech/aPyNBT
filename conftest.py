# -*- coding: utf-8 -*-
""" pytest configuration
"""

import os
from pathlib import Path
import random
import re
import time
from typing import List, Tuple

import line_profiler
import pytest

import nbt

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
    return nbt_files


# Initialized in pytest_configure()
FILEPATH_FILES: List[Path] = None
FILEPATH_IDS: List[str] = None


def pytest_addoption(parser):
    g = parser.getgroup("Minecraft NBT Test Files")
    g.addoption("--shuffle-files", action="store_true", dest="shuffle-files", help="Shuffle lists of files")
    g.addoption("--repeat-files", action="store", type=int, default=1, dest="repeat-files", help="Number of times to test all files")
    g.addoption("--limit-files", action="store", type=int, default=-1, dest="limit-files", help="Cap the number files")
    g.addoption("--no-file-ids", action="store_true", dest="no-file-ids", help="Don't create test IDs out of filenames")
    g.addoption("--no-nbt-profiling", action="store_true", dest="no-nbt-profiling", help="Don't profile the nbt module during unit tests")


PROFILING_NBT = True


def pytest_configure(config):
    global FILEPATH_FILES, FILEPATH_IDS, PROFILING_NBT
    FILEPATH_FILES = []

    # --no-nbt-profiling
    PROFILING_NBT = not config.getoption("no-nbt-profiling")
    if PROFILING_NBT:
        if not os.path.exists("nbt_prof"):
            os.mkdir("nbt_prof")
        assert os.path.isdir("nbt_prof")

    # --limit-files
    max_files = config.getoption("limit-files")

    # Skip finding files if the limit is zero
    if max_files == 0:
        return

    FILEPATH_FILES = _find_all_test_data()

    # --repeat-files
    if config.getoption("repeat-files") > 0:
        filepath_files = []
        for _ in range(config.getoption("repeat-files")):
            filepath_files.extend(FILEPATH_FILES)
        FILEPATH_FILES = filepath_files

    # --shuffle-files
    if config.getoption("shuffle-files"):
        # Ruin the natural ordering and locality from directory traversal.
        # Similar files (such as player data) will trigger the same code paths
        # which get optimized easily by modern* CPUs.
        #
        # * Modern meaning most x86_64; definitely not all RISC variants...
        random.shuffle(FILEPATH_FILES)

    if max_files > 0:
        FILEPATH_FILES = FILEPATH_FILES[:max_files]

    # --no-file-ids
    if not config.getoption("no-file-ids"):
        FILEPATH_IDS = [str(filepath) for filepath in FILEPATH_FILES]


CURRENT_TIME = int(time.time() * 1000)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if not PROFILING_NBT:
        return

    lp = line_profiler.LineProfiler()
    lp.add_module(nbt)
    lp.enable_by_count()
    yield
    lp.disable_by_count()
    profile_name = re.sub(r"[^-a-zA-Z0-9_\.]", "_", item.name)
    lp.dump_stats(f"nbt_prof/{profile_name}.{CURRENT_TIME}.prof")


def pytest_generate_tests(metafunc):
    if "filepath" in metafunc.fixturenames:
        metafunc.parametrize("filepath", FILEPATH_FILES, ids=FILEPATH_IDS)

