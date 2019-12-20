# -*- coding: utf-8 -*-
""" pytest configuration
"""

import hashlib
import os
from pathlib import Path
import pickle
import random
import re
import time
from typing import Dict, List, Tuple

import line_profiler
import _line_profiler
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

PROFILING_PUBLIC_DIR = Path("perf/Public/")
PROFILING_PRIVATE_DIR = Path("perf/Private/")


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
    g = parser.getgroup("aPyNBT Test Control")
    g.addoption("--shuffle-files", action="store_true", dest="shuffle-files", help="Shuffle lists of files")
    g.addoption("--repeat-files", action="store", type=int, default=1, dest="repeat-files", help="Number of times to test all files")
    g.addoption("--limit-files", action="store", type=int, default=-1, dest="limit-files", help="Cap the number files")
    g.addoption("--file-ids", action="store_true", dest="file-ids", help="Don't create test IDs out of filenames")
    g.addoption("--nbt-profiling", action="store_true", dest="nbt-profiling", help="Profile the nbt module during unit test execution")
    g.addoption("--public-profiling", action="store_true", dest="public-profiling", help="Save per-test prof data named as hashed test parameter ids")
    g.addoption("--pertest-profiling", action="store_true", dest="pertest-profiling", help="Save prof data for each test & parameter combination")


PROFILING_NBT = False
PUBLIC_PROFILING = False


def pytest_configure(config):
    global FILEPATH_FILES, FILEPATH_IDS, PERTEST_PROFILING, PROFILING_NBT, PUBLIC_PROFILING
    FILEPATH_FILES = []

    # --nbt-profiling
    PROFILING_NBT = config.getoption("nbt-profiling")
    if PROFILING_NBT:
        try:
            PROFILING_PRIVATE_DIR.mkdir()
        except FileExistsError:
            pass

    # --public-profiling
    PUBLIC_PROFILING = config.getoption("public-profiling")
    if PUBLIC_PROFILING:
        try:
            PROFILING_PUBLIC_DIR.mkdir()
        except FileExistsError:
            pass

    # --pertest-profiling
    PERTEST_PROFILING = config.getoption("pertest-profiling")

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

    # --file-ids
    if config.getoption("file-ids"):
        FILEPATH_IDS = [str(filepath) for filepath in FILEPATH_FILES]


CURRENT_TIME = int(time.time() * 1000)
AGGREGATE_STATS = None


def merge_line_stats(base: _line_profiler.LineStats, incr: _line_profiler.LineStats) -> None:
    """ base += incr

    LineStats.timings: Dict[Tuple[str, str, str], List[Tuple[const int, int, int]]]
    """
    # key -> (filename, first line number, function name)
    # value -> [(line number, hit count, total time), ...]
    for key, new_values in incr.timings.items():

        if key not in base.timings:
            base.timings[key] = incr.timings[key]
            continue

        line_to_hits: Dict[int, int] = {}
        line_to_time: Dict[int, int] = {}

        for base_value in base.timings[key]:
            lineno, hits, tottime = base_value
            line_to_hits[lineno] = hits
            line_to_time[lineno] = tottime

        for new_value in new_values:
            lineno, hits, tottime = new_value
            if lineno in line_to_hits.keys():
                line_to_hits[lineno] += hits
                line_to_time[lineno] += tottime
                continue
            line_to_hits[lineno] = hits
            line_to_time[lineno] = tottime

        base.timings[key] = []
        for lineno in sorted(list(line_to_hits.keys())):
            base.timings[key].append((lineno, line_to_hits[lineno], line_to_time[lineno]))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if not PROFILING_NBT:
        yield
        return

    lp = line_profiler.LineProfiler()
    lp.add_module(nbt)
    lp.enable_by_count()
    yield
    lp.disable_by_count()

    # All private profiling results are compiled and saved into one statistic.
    # This singular statistic is saved in the Public/ directory.
    global AGGREGATE_STATS
    if AGGREGATE_STATS is None:
        AGGREGATE_STATS = lp.get_stats()
    else:
        merge_line_stats(AGGREGATE_STATS, lp.get_stats())
    with open(PROFILING_PUBLIC_DIR / f"aggregate.prof", 'wb') as f:
        pickle.dump(AGGREGATE_STATS, f, pickle.HIGHEST_PROTOCOL)
    with open(PROFILING_PUBLIC_DIR / f"aggregate.stats", 'w') as f:
        line_profiler.show_text(AGGREGATE_STATS.timings, AGGREGATE_STATS.unit, stream=f)


    # Profiling results will always have individual entries in the Private/
    # directory. Item name hashing and saving to the public directory can be
    # enabled with --public-profiling.
    if not PERTEST_PROFILING:
        return
    profile_name = re.sub(r"[^-a-zA-Z0-9_\.]", "_", item.name)
    lp.dump_stats(PROFILING_PRIVATE_DIR / f"{profile_name}.prof")
    with open(PROFILING_PRIVATE_DIR / f"{profile_name}.stats", 'w') as f:
        lp.print_stats(stream=f)
    if PUBLIC_PROFILING:
        profile_name_hashed = hashlib.blake2b(
            profile_name.encode('utf-8'),
            digest_size=3
        ).hexdigest()
        lp.dump_stats(PROFILING_PUBLIC_DIR / f"{profile_name_hashed}.prof")
        with open(PROFILING_PUBLIC_DIR / f"{profile_name_hashed}.stats", 'w') as f:
            lp.print_stats(stream=f)


def pytest_generate_tests(metafunc):
    if "filepath" in metafunc.fixturenames:
        metafunc.parametrize("filepath", FILEPATH_FILES, ids=FILEPATH_IDS)

