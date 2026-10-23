import re
import time

from src.libs.ids import new_artifact_id, new_generation_id, new_ulid

ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def test_ulid_format():
    assert ULID.match(new_ulid())


def test_prefixed_ids_fit_the_32_char_columns():
    gen, art = new_generation_id(), new_artifact_id()

    assert gen.startswith("gen_") and len(gen) == 30
    assert art.startswith("art_") and len(art) == 30


def test_ulids_sort_by_creation_time():
    first = new_ulid()
    time.sleep(0.002)
    second = new_ulid()

    assert first < second
