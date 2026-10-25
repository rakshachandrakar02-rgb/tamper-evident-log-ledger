import json, sqlite3
from blockchain import Ledger


def make_ledger(tmp_path):
    l = Ledger(str(tmp_path / "test.db"))
    for i in range(3):
        l.add_log("test", "INFO", f"event {i}")
    l.seal()
    return l


def test_clean_chain_is_valid(tmp_path):
    assert make_ledger(tmp_path).verify()[0] is True


def test_edited_log_is_detected(tmp_path):
    l = make_ledger(tmp_path)
    b = l.blocks()[1]
    b["logs"][0]["message"] = "hacked"
    with sqlite3.connect(l.path) as c:
        c.execute("UPDATE blocks SET logs=? WHERE idx=1", (json.dumps(b["logs"]),))
    ok, problems = l.verify()
    assert ok is False and problems[0]["block"] == 1


def test_deleted_block_is_detected(tmp_path):
    l = make_ledger(tmp_path)
    head = l.blocks()[-1]["hash"]
    with sqlite3.connect(l.path) as c:
        c.execute("DELETE FROM blocks WHERE idx=1")
    assert l.verify(anchor=head)[0] is False