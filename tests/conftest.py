# -*- coding: utf-8 -*-
""" pytest configuration
"""

import hashlib
from pathlib import Path
import pickle
import random
import re
import time
from typing import Dict, List, Tuple

import line_profiler
import _line_profiler
import pytest

import aPyNBT.nbt as nbt

# Search for files starting in this directory:
DEFAULT_TEST_DATA_PATH = Path("tests/data/")

# Consider files with these extensions to contain NBT data (compressed or uncompressed):
NBT_FILE_SUFFIXES: Tuple[str] = (".dat",)
ANVIL_FILE_SUFFIXES: Tuple[str] = (".mca",)
REGION_FILE_SUFFIXES: Tuple[str] = (".mcr",)

# These files will be ignored:
TEST_FILE_BLACKLIST: Tuple[str] = (
    "uid.dat",  # Undocumented. Maybe related to Realms?
                # https://www.minecraftforum.net/forums/minecraft-java-edition/suggestions/79149-world-uid-for-multi-world-servers
)

PROFILING_PUBLIC_DIR = Path("perf/Public/")
PROFILING_PRIVATE_DIR = Path("perf/Private/")


def _find_all_test_data(root: Path, exts: Tuple[str] = None) -> List[Path]:
    """ Search and return testable files based on suffix
    """
    files = []
    for f in root.iterdir():
        if f.is_dir():
            files.extend(_find_all_test_data(f, exts=exts))
            continue
        if f.is_file():
            if any([f.name.endswith(suffix) for suffix in exts]):
                if f.name not in TEST_FILE_BLACKLIST:
                    files.append(f)
                    continue
    return files


# Initialized in pytest_configure()
NBT_FILEPATH_FILES: List[Path] = None
NBT_FILEPATH_IDS: List[str] = None
ANVIL_FILEPATH_FILES: List[Path] = None
ANVIL_FILEPATH_IDS: List[str] = None
REGION_FILEPATH_FILES: List[Path] = None
REGION_FILEPATH_IDS: List[str] = None


def pytest_addoption(parser):
    g = parser.getgroup("aPyNBT Test Control")
    g.addoption("--shuffle-files", action="store_true", dest="shuffle-files", help="Shuffle lists of files")
    g.addoption("--repeat-files", action="store", type=int, default=1, dest="repeat-files", help="Number of times to test all files")
    g.addoption("--limit-nbt-files", action="store", type=int, default=-1, dest="limit-nbt-files", help="Cap the number of data files used for testing (nbt)")
    g.addoption("--limit-region-files", action="store", type=int, default=8, dest="limit-region-files", help="Cap the number of data files used for testing (region)")
    g.addoption("--limit-anvil-files", action="store", type=int, default=8, dest="limit-anvil-files", help="Cap the number of data files used for testing (anvil)")
    g.addoption("--file-ids", action="store_true", dest="file-ids", help="Don't create test IDs out of filenames")
    g.addoption("--nbt-profiling", action="store_true", dest="nbt-profiling", help="Profile the nbt module during unit test execution")
    g.addoption("--public-profiling", action="store_true", dest="public-profiling", help="Save per-test prof data named as hashed test parameter ids")
    g.addoption("--pertest-profiling", action="store_true", dest="pertest-profiling", help="Save prof data for each test & parameter combination")
    g.addoption("--test-data-dir", action="store", type=str, default=None, dest="test-data-dir", help="Search for NBT/Region files in this directory")


PROFILING_NBT = False
PUBLIC_PROFILING = False


def pytest_configure(config):
    global \
        NBT_FILEPATH_FILES, NBT_FILEPATH_IDS, \
        ANVIL_FILEPATH_FILES, ANVIL_FILEPATH_IDS, \
        REGION_FILEPATH_FILES, REGION_FILEPATH_IDS, \
        PERTEST_PROFILING, PROFILING_NBT, PUBLIC_PROFILING

    NBT_FILEPATH_FILES = []
    ANVIL_FILEPATH_FILES = []
    REGION_FILEPATH_FILES = []

    # --nbt-profiling
    PROFILING_NBT = config.getoption("nbt-profiling")
    if PROFILING_NBT:
        try:
            PROFILING_PRIVATE_DIR.mkdir()
        except FileExistsError:
            pass

        # Public/ is used for the aggregate stats.
        try:
            PROFILING_PUBLIC_DIR.mkdir()
        except FileExistsError:
            pass

    # --public-profiling
    PUBLIC_PROFILING = config.getoption("public-profiling")

    # --pertest-profiling
    PERTEST_PROFILING = config.getoption("pertest-profiling")

    # --test-data-dir
    test_data_root = DEFAULT_TEST_DATA_PATH
    if config.getoption("test-data-dir") is not None:
        test_data_root = Path(config.getoption("test-data-dir"))

    # Find files to use as test parameters
    NBT_FILEPATH_FILES = _find_all_test_data(root=test_data_root, exts=NBT_FILE_SUFFIXES)
    ANVIL_FILEPATH_FILES = _find_all_test_data(root=test_data_root, exts=ANVIL_FILE_SUFFIXES)
    REGION_FILEPATH_FILES = _find_all_test_data(root=test_data_root, exts=REGION_FILE_SUFFIXES)

    # --repeat-files
    if config.getoption("repeat-files") > 0:
        nbt_filepath_files = []
        for _ in range(config.getoption("repeat-files")):
            nbt_filepath_files.extend(NBT_FILEPATH_FILES)
        NBT_FILEPATH_FILES = nbt_filepath_files

    # --shuffle-files
    if config.getoption("shuffle-files"):
        # Ruin the natural ordering and locality from directory traversal.
        # Similar files (such as player data) will trigger the same code paths
        # which get optimized easily by modern* CPUs.
        #
        # * Modern meaning most x86_64; definitely not all RISC variants...
        random.shuffle(NBT_FILEPATH_FILES)

    # --limit-files
    max_nbt_files = config.getoption("limit-nbt-files")
    max_anvil_files = config.getoption("limit-anvil-files")
    max_region_files = config.getoption("limit-region-files")

    if max_nbt_files >= 0:
        NBT_FILEPATH_FILES = NBT_FILEPATH_FILES[:max_nbt_files]

    if max_anvil_files >= 0:
        ANVIL_FILEPATH_FILES = ANVIL_FILEPATH_FILES[:max_anvil_files]

    if max_region_files >= 0:
        REGION_FILEPATH_FILES = REGION_FILEPATH_FILES[:max_region_files]

    # --file-ids
    if config.getoption("file-ids"):
        NBT_FILEPATH_IDS = [str(nbt_filepath) for nbt_filepath in NBT_FILEPATH_FILES]
        ANVIL_FILEPATH_IDS = [str(anvil_filepath) for anvil_filepath in ANVIL_FILEPATH_FILES]
        REGION_FILEPATH_IDS = [str(region_filepath) for region_filepath in REGION_FILEPATH_FILES]


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
    if "nbt_filepath" in metafunc.fixturenames:
        metafunc.parametrize("nbt_filepath", NBT_FILEPATH_FILES, ids=NBT_FILEPATH_IDS)
    if "region_filepath" in metafunc.fixturenames:
        metafunc.parametrize("region_filepath", REGION_FILEPATH_FILES, ids=REGION_FILEPATH_IDS)
    if "anvil_filepath" in metafunc.fixturenames:
        metafunc.parametrize("anvil_filepath", ANVIL_FILEPATH_FILES, ids=ANVIL_FILEPATH_IDS)
