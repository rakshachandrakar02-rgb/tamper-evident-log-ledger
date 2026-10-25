# Blockchain-Based Tamper-Evident Security Log System

Collects security logs and Android permission changes, seals them into hash-chained,
Merkle-rooted, proof-of-work blocks, and detects any edit or deletion of past records.

## Run locally
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set API_KEY=mysecret
python app.py          (open http://localhost:5000)

## Collect data
python collector.py fake.log http://localhost:5000 mysecret
python permission_audit.py http://localhost:5000 mysecret --demo

## Test
pytest