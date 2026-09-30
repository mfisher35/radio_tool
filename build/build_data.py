import json, re, unicodedata, collections

raw = json.load(open("stations.json"))

COUNTRY_FIX = {
    "The United States Of America": "United States",
    "The United Kingdom Of Great Britain And Northern Ireland": "United Kingdom",
    "The Russian Federation": "Russia",
    "The Netherlands": "Netherlands",
    "The Czech Republic": "Czechia",
    "The Republic Of Korea": "South Korea",
    "The Democratic People's Republic Of Korea": "North Korea",
    "The Republic Of Moldova": "Moldova",
    "The Syrian Arab Republic": "Syria",
    "The Islamic Republic Of Iran": "Iran",
    "The United Republic Of Tanzania": "Tanzania",
    "The Dominican Republic": "Dominican Republic",
    "The Philippines": "Philippines",
    "The Bahamas": "Bahamas",
    "The Gambia": "Gambia",
    "The Sudan": "Sudan",
    "The Niger": "Niger",
    "The Congo": "Congo",
    "The Democratic Republic Of The Congo": "DR Congo",
    "The United Arab Emirates": "United Arab Emirates",
    "The Lao People's Democratic Republic": "Laos",
    "The Plurinational State Of Bolivia": "Bolivia",
    "The Bolivarian Republic Of Venezuela": "Venezuela",
    "The Republic Of North Macedonia": "North Macedonia",
    "The Central African Republic": "Central African Republic",
    "The Cayman Islands": "Cayman Islands",
    "The Cook Islands": "Cook Islands",
    "The Faroe Islands": "Faroe Islands",
    "The Falkland Islands": "Falkland Islands",
    "The Marshall Islands": "Marshall Islands",
    "The Turks And Caicos Islands": "Turks and Caicos",
    "The Comoros": "Comoros",
}

WS = re.compile(r"\s+")


def clean_name(n):
    n = WS.sub(" ", (n or "")).strip()
    n = n.strip(" -–—_*|.·•")
    return n[:80]


def norm_key(n):
    n = unicodedata.normalize("NFKD", (n or "").lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", n)


def norm_url(u):
    u = (u or "").strip()
    u = re.sub(r"^https?://", "", u, flags=re.I)
    return u.rstrip("/").lower()


TAG_BLOCK = {
    "radio", "fm", "am", "music", "musica", "música", "estación",
    "estacion", "internet radio", "radio station", "online", "stream",
    "webradio", "web radio", "moi merino", "norteamérica", "norteamerica",
    "américa", "america", "latinoamérica", "latinoamerica",
    "entretenimiento", "la mejor", "varios", "misc", "general", "various",
    "other", "s", "-", "1", "2", "0", "radio online", "online radio",
}


def split_tags(t):
    out = []
    for x in (t or "").split(","):
        x = WS.sub(" ", x.strip().lower())
        if not x or len(x) > 28 or x in TAG_BLOCK:
            continue
        if x not in out:
            out.append(x)
        if len(out) >= 8:
            break
    return out


def split_langs(l):
    out = []
    for x in (l or "").split(","):
        x = WS.sub(" ", x.strip().lower())
        if not x or len(x) > 24:
            continue
        if x not in out:
            out.append(x)
        if len(out) >= 3:
            break
    return out


# ---- dedupe: same stream URL, then same name within a country -----------
best = {}
for s in raw:
    name = clean_name(s.get("name"))
    url = (s.get("url_resolved") or s.get("url") or "").strip()
    if not name or not url or not url.lower().startswith(("http://", "https://")):
        continue
    if len(url) > 400:
        continue
    score = (s.get("clickcount") or 0) * 2 + (s.get("votes") or 0)
    k = norm_url(url)
    prev = best.get(k)
    if prev is None or score > prev[0]:
        best[k] = (score, name, url, s)

by_name = {}
for score, name, url, s in best.values():
    k2 = (norm_key(name), (s.get("countrycode") or "").upper())
    if not k2[0]:
        k2 = (norm_url(url), "")
    prev = by_name.get(k2)
    if prev is None or score > prev[0]:
        by_name[k2] = (score, name, url, s)

rows_src = sorted(by_name.values(), key=lambda t: -t[0])
print("raw:", len(raw), "-> unique url:", len(best), "-> final:", len(rows_src))


class Dict_:
    def __init__(self):
        self.items = []
        self.idx = {}

    def add(self, v):
        if v in self.idx:
            return self.idx[v]
        self.idx[v] = len(self.items)
        self.items.append(v)
        return self.idx[v]


countries, langs, tags, codecs, states = Dict_(), Dict_(), Dict_(), Dict_(), Dict_()

stations = []
for score, name, url, s in rows_src:
    country = COUNTRY_FIX.get(s.get("country") or "", WS.sub(" ", (s.get("country") or "")).strip())
    cc = (s.get("countrycode") or "").upper()
    ci = countries.add(country + "\t" + cc) if country else -1
    st = WS.sub(" ", (s.get("state") or "").strip())[:40]
    si = states.add(st) if st else -1
    li = [langs.add(x) for x in split_langs(s.get("language"))]
    ti = [tags.add(x) for x in split_tags(s.get("tags"))]
    codec = (s.get("codec") or "").upper().replace("UNKNOWN", "").strip(",")
    kd = codecs.add(codec) if codec else -1
    # some stations report bits/sec (128000) instead of kbps; anything still
    # above CD rate after that is junk, so drop it to "unknown"
    br = int(s.get("bitrate") or 0)
    if br >= 8000:
        br //= 1000
    if br > 1411 or br < 0:
        br = 0
    hp = (s.get("homepage") or "").strip()
    hp = "" if len(hp) > 160 else hp
    sch = 1 if url.lower().startswith("https://") else 0
    u = re.sub(r"^https?://", "", url, flags=re.I)
    hsch = 1 if hp.lower().startswith("https://") else 0
    h = re.sub(r"^https?://", "", hp, flags=re.I).rstrip("/") if hp else ""
    stations.append([
        name, u, sch, h, hsch, ci, si, li, ti, kd, br,
        int(s.get("votes") or 0), int(s.get("clickcount") or 0),
        1 if (s.get("hls") or 0) else 0,
    ])

data = {
    "v": 1,
    "generated": "2026-09-30",
    "countries": countries.items,
    "states": states.items,
    "langs": langs.items,
    "tags": tags.items,
    "codecs": codecs.items,
    "stations": stations,
}
js = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
open("data.json", "w").write(js)
nb = len(js.encode())
print("json bytes: %d (%.2f MB)" % (nb, nb / 1e6))
print("countries:", len(countries.items), "states:", len(states.items),
      "langs:", len(langs.items), "tags:", len(tags.items), "codecs:", codecs.items)
print("sample:", json.dumps(stations[0], ensure_ascii=False))
tc = collections.Counter(t for r in stations for t in r[8])
print("top tags:", [(tags.items[i], c) for i, c in tc.most_common(40)])
print("stations with >=1 tag:", sum(1 for r in stations if r[8]))
print("https share: %.1f%%" % (100 * sum(1 for r in stations if r[2]) / len(stations)))
