import os, json, sqlite3
from flask import Flask, jsonify, request, render_template, abort
from blockchain import Ledger

app = Flask(__name__)
ledger = Ledger(os.getenv("LEDGER_DB", "ledger.db"))
API_KEY = os.getenv("API_KEY", "change-me")
DEMO = os.getenv("DEMO_MODE", "1") == "1"   # shows the "attacker" button; use 0 in production


def need_key():
    if request.headers.get("X-API-Key") != API_KEY:
        abort(401, "Missing or wrong X-API-Key")


@app.get("/")
def home():
    return render_template("index.html", demo=DEMO)


@app.post("/api/logs")
def add_log():
    need_key()
    d = request.get_json(force=True)
    if not d.get("message"):
        abort(400, "message is required")
    sealed = ledger.add_log(d.get("source", "unknown"), d.get("level", "INFO"), d["message"])
    return jsonify(status="stored", sealed_block=sealed, pending=ledger.pending_count()), 201


@app.post("/api/seal")
def seal():
    need_key()
    return jsonify(sealed_block=ledger.seal())


@app.get("/api/chain")
def chain():
    return jsonify(blocks=ledger.blocks(), pending=ledger.pending_count())


@app.get("/api/verify")
def verify():
    ok, problems = ledger.verify(request.args.get("anchor"))
    return jsonify(valid=ok, problems=problems, head=ledger.blocks()[-1]["hash"])


@app.post("/api/demo/tamper")
def tamper():
    """Plays the attacker: edits the database directly, bypassing our code."""
    if not DEMO:
        abort(404)
    target = next((b for b in ledger.blocks() if b["idx"] > 0), None)
    if not target:
        abort(400, "Seal at least one block first")
    target["logs"][0]["message"] = "[EDITED BY ATTACKER] nothing suspicious here"
    with sqlite3.connect(ledger.path) as c:
        c.execute("UPDATE blocks SET logs=? WHERE idx=?", (json.dumps(target["logs"]), target["idx"]))
    return jsonify(tampered_block=target["idx"])


@app.errorhandler(401)
@app.errorhandler(400)
def err(e):
    return jsonify(error=e.description), e.code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))