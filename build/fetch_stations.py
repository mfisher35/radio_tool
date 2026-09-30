import json, urllib.request, time, sys

BASES = ["https://de1.api.radio-browser.info", "https://all.api.radio-browser.info"]
UA = "radio-tool/1.0 (personal station browser)"
PAGE = 4000
out = []
offset = 0
bi = 0
while True:
    base = BASES[bi % len(BASES)]
    url = (f"{base}/json/stations/search?hidebroken=true&order=clickcount"
           f"&reverse=true&limit={PAGE}&offset={offset}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            chunk = json.load(r)
    except Exception as e:
        print(f"  retry offset={offset}: {e}", file=sys.stderr)
        bi += 1
        time.sleep(2)
        continue
    if not chunk:
        break
    out.extend(chunk)
    print(f"offset={offset} got={len(chunk)} total={len(out)}", file=sys.stderr)
    offset += PAGE
    if len(chunk) < PAGE:
        break
    time.sleep(0.4)

json.dump(out, open("stations.json", "w"))
print("FINAL", len(out), file=sys.stderr)
