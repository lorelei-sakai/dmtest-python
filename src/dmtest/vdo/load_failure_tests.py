from dmtest.assertions import assert_matches, assert_string_in
from dmtest.vdo.utils import standard_vdo, standard_stack
from dmtest.utils import get_dmesg_log, trash_device
import logging as log
import time

def try_a_bad_value(fix, expected_message, **opts):
    start_time = time.time()
    stack = standard_stack(fix, **opts)
    started = False
    try:
        with stack.activate():
            started = True
    except:
        message = get_dmesg_log(start_time)
        log.info(message)
        assert_string_in(message, expected_message)
        assert_string_in(message, "Bad configuration option")
        assert_string_in(message, "ioctl: error adding target to table")
    if started:
        raise AssertionError("VDO device shouldn't have started")

def t_bad_values(fix):
    # Test thread/zone counts exceeding hard-coded limits.
    format = True
    max_threads = {
        "bio":      100,
        "bioAck":   100,
        "cpu":      100,
        "hashZone": 100,
        "logical":   60,
        "physical":  16,
    }
    for (thread_type, max_count) in max_threads.items():
        # format the first time only
        opts : dict[str, bool | int] = { "format": format }
        format = False
        # out of range value
        opts[thread_type] = max_count + 1
        try_a_bad_value(fix,
                        f"thread config string error: at most {max_count} '{thread_type}' threads are allowed",
                        **opts)
        # parsing only handles 32-bit numbers
        opts["format"] = False
        opts[thread_type] = 1 << 32
        try_a_bad_value(fix, "integer value needed", **opts)
    # To be tested: physical zones exceeds slab count


def t_corrupt_geometry(fix):
    # Test trying to start when the geometry block has been clobbered.
    with standard_vdo(fix) as vdo:
        pass
    start_time = time.time()
    # Overwrite just one (4kB) block with random data
    trash_device(fix.cfg["data_dev"], 8)
    stack = standard_stack(fix, format = False)
    started = False
    try:
        with stack.activate():
            started = True
    except:
        message = get_dmesg_log(start_time)
        log.info(message)
        assert_matches(message, r"Could not (load|parse) geometry block")
    if started:
        raise AssertionError("VDO device shouldn't have started")


def register(tests):
    tests.register_batch(
        "/vdo/load_failure/",
        [
            ("bad_values", t_bad_values),
            ("corrupt_geometry", t_corrupt_geometry),
        ],
    )
