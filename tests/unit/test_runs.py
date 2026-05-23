import re

from socialgraph.runs import new_run_id


def test_new_run_id_format():
    rid = new_run_id()
    # format: YYYYMMDDTHHMMSSZ_<6hex>
    assert re.match(r"^\d{8}T\d{6}Z_[0-9a-f]{6}$", rid), f"bad run_id: {rid!r}"


def test_new_run_id_unique():
    ids = {new_run_id() for _ in range(50)}
    assert len(ids) == 50  # UUID hex suffix ensures uniqueness
