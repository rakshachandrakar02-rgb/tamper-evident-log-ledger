import json, os, re, subprocess, sys
import requests

BASELINE = "baseline.json"
DANGEROUS = {"CAMERA", "RECORD_AUDIO", "READ_SMS", "SEND_SMS", "RECEIVE_SMS",
             "READ_CONTACTS", "READ_CALL_LOG", "ACCESS_FINE_LOCATION",
             "ACCESS_BACKGROUND_LOCATION", "SYSTEM_ALERT_WINDOW",
             "BIND_ACCESSIBILITY_SERVICE", "READ_EXTERNAL_STORAGE"}


def adb(*args):
    return subprocess.run(["adb", *args], capture_output=True, text=True, check=True).stdout


def parse_perms(dump):
    """Works on Android 6+ (granted=true) and Android 5 and older (grantedPermissions:)."""
    perms = set(re.findall(r"([\w.]+): granted=true", dump))
    on = False
    for line in dump.splitlines():
        s = line.strip()
        if s == "grantedPermissions:":
            on = True
        elif on and re.fullmatch(r"[\w.]+", s):
            perms.add(s)
        elif on and s:
            on = False
    return sorted(p.split(".")[-1] for p in perms)


def scan(demo=False):
    """Return {package: [granted permissions]}.
    Demo mode reads fake_phone.json instead of a real phone."""
    if demo:
        return json.load(open("fake_phone.json"))
    out = adb("shell", "pm", "list", "packages", "-3")
    pkgs = [l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("package:")]
    result = {}
    for p in pkgs:
        result[p] = parse_perms(adb("shell", "dumpsys", "package", p))
    return result


def compare(old, new):
    events = []
    for pkg, perms in new.items():
        if pkg not in old:
            risky = sorted(set(perms) & DANGEROUS)
            events.append(("WARN" if risky else "INFO",
                           f"New app installed: {pkg} | risky permissions: {risky or 'none'}"))
            continue
        added = sorted(set(perms) - set(old[pkg]))
        if added:
            risky = sorted(set(added) & DANGEROUS)
            events.append(("WARN" if risky else "INFO",
                           f"Permission granted to {pkg}: {added}"))
    for pkg in old:
        if pkg not in new:
            events.append(("INFO", f"App removed: {pkg}"))
    return events


if __name__ == "__main__":
    demo = "--demo" in sys.argv
    url, key = [a for a in sys.argv[1:] if a != "--demo"][:2]
    headers = {"X-API-Key": key}
    new = scan(demo)
    if os.path.exists(BASELINE):
        events = compare(json.load(open(BASELINE)), new)
    else:
        events = [("INFO", f"Baseline created: {len(new)} apps scanned")]
    for level, msg in events:
        requests.post(f"{url}/api/logs", headers=headers, timeout=10,
                      json={"source": "android-audit", "level": level, "message": msg})
        print(level, msg)
    requests.post(f"{url}/api/seal", headers=headers, timeout=10)
    json.dump(new, open(BASELINE, "w"), indent=2)
    print("Done:", len(events), "event(s) sent")