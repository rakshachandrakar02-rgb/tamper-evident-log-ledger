# Blockchain-Based Tamper-Evident Security Log System

**Live demo:** https://tamper-evident-log-ledger.onrender.com/

A security log system that makes tampering visible. Logs are grouped into blocks, hashed with SHA-256, linked into a chain and mined with a small proof-of-work. If anyone edits or deletes a past record, verification fails and names the exact block that was changed.

It collects two kinds of data:
- Server-style security logs (from a log file or typed in the dashboard)
- Android app permission changes (new apps, newly granted permissions)

## Why this exists

An attacker who breaks into a server often edits the logs to hide what they did. A normal log file can be changed silently. This system keeps cryptographic evidence of integrity, so changes are detected.

## How it works

1. **Log:** each event has a timestamp, source, level and message.
2. **Merkle root:** every log is hashed, then hashes are paired and re-hashed until one root remains. Changing any log changes the root.
3. **Block:** index, timestamp, previous block's hash, Merkle root and nonce.
4. **Chain:** each block stores the previous block's hash, so editing block N breaks every later block.
5. **Proof-of-work:** the nonce is searched until the block hash starts with `000`, which makes rewriting history costly.
6. **Verification:** recomputes everything and reports edited logs, edited headers, missing proof-of-work, broken links and (with an anchor) deleted blocks.

## Project structure

| File | Purpose |
|---|---|
| `blockchain.py` | Core ledger: hashing,