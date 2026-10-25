import sys, time, requests


def follow(path):
    """Yield new lines as they are appended to the file, like `tail -f`."""
    with open(path, "r", errors="replace") as f:
        f.seek(0, 2)                     # jump to the end, so only NEW lines are read
        while True:
            line = f.readline()
            if line:
                yield line.strip()
            else:
                time.sleep(0.5)


if __name__ == "__main__":
    path, url, key = sys.argv[1:4]
    for line in follow(path):
        if not line:
            continue
        suspicious = any(w in line.lower() for w in ("fail", "denied", "invalid"))
        level = "WARN" if suspicious else "INFO"
        try:
            requests.post(f"{url}/api/logs",
                          headers={"X-API-Key": key}, timeout=5,
                          json={"source": path, "level": level, "message": line})
            print("sent:", line)
        except requests.RequestException as e:
            print("send failed:", e)