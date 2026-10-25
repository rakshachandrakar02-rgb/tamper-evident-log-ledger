import hashlib, json, sqlite3, time

DIFFICULTY = 3                 # a valid block hash must start with "000"
GENESIS_PREV = "0" * 64        # the first block has no parent


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def merkle_root(logs: list) -> str:
    level = [sha256(json.dumps(l, sort_keys=True)) for l in logs] or [sha256("")]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [sha256(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def block_hash(idx, ts, prev, root, nonce) -> str:
    return sha256(f"{idx}|{ts}|{prev}|{root}|{nonce}")


class Ledger:
    def __init__(self, path="ledger.db"):
        self.path = path
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS blocks(
                idx INTEGER PRIMARY KEY, ts REAL, prev TEXT,
                root TEXT, nonce INTEGER, hash TEXT, logs TEXT)""")
            c.execute("""CREATE TABLE IF NOT EXISTS pending(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL, source TEXT, level TEXT, message TEXT)""")
        if not self.blocks():
            self._mine([{"ts": time.time(), "source": "system",
                         "level": "INFO", "message": "Genesis block"}])

    def _db(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def blocks(self):
        with self._db() as c:
            rows = c.execute("SELECT * FROM blocks ORDER BY idx").fetchall()
        return [{**dict(r), "logs": json.loads(r["logs"])} for r in rows]

    def pending_count(self):
        with self._db() as c:
            return c.execute("SELECT COUNT(*) FROM pending").fetchone()[0]

    def add_log(self, source, level, message, auto_seal=5):
        with self._db() as c:
            c.execute("INSERT INTO pending(ts,source,level,message) VALUES(?,?,?,?)",
                      (time.time(), source, level, message))
        if self.pending_count() >= auto_seal:
            return self.seal()

    def seal(self):
        with self._db() as c:
            rows = c.execute("SELECT ts,source,level,message FROM pending ORDER BY id").fetchall()
            if not rows:
                return None
            logs = [dict(r) for r in rows]
            c.execute("DELETE FROM pending")
        return self._mine(logs)

    def _mine(self, logs):
        chain = self.blocks()
        idx = len(chain)
        prev = chain[-1]["hash"] if chain else GENESIS_PREV
        root, ts, nonce = merkle_root(logs), time.time(), 0
        while True:
            h = block_hash(idx, ts, prev, root, nonce)
            if h.startswith("0" * DIFFICULTY):
                break
            nonce += 1
        with self._db() as c:
            c.execute("INSERT INTO blocks VALUES(?,?,?,?,?,?,?)",
                      (idx, ts, prev, root, nonce, h, json.dumps(logs)))
        return idx

    def verify(self, anchor=None):
        problems, chain = [], self.blocks()
        for i, b in enumerate(chain):
            if merkle_root(b["logs"]) != b["root"]:
                problems.append({"block": b["idx"], "issue":
                    "Log contents do not match the stored Merkle root (logs edited or deleted)"})
            if block_hash(b["idx"], b["ts"], b["prev"], b["root"], b["nonce"]) != b["hash"]:
                problems.append({"block": b["idx"], "issue": "Block hash is invalid (header edited)"})
            if not b["hash"].startswith("0" * DIFFICULTY):
                problems.append({"block": b["idx"], "issue": "Proof-of-work missing"})
            expected = chain[i - 1]["hash"] if i else GENESIS_PREV
            if b["prev"] != expected:
                problems.append({"block": b["idx"], "issue":
                    "Chain link broken (previous block changed or removed)"})
        if anchor and not any(b["hash"] == anchor for b in chain):
            problems.append({"block": None, "issue":
                "Anchored head hash not found (blocks deleted or rewritten)"})
        return (not problems), problems