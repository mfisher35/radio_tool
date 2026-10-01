"""Drop every station a browser on an https:// page could not actually play.

Connects to each stream the way the hosted page would: over https only (plain
http is blocked there as mixed content, so http-only stations are retried on
https and dropped if that fails), with certificate checks, following redirects
but never onto http, and reading the first few KB to make sure audio comes
back rather than an error page. HLS playlists also need CORS headers, because
outside Safari they are fetched by hls.js.

Rewrites data.json in place. Takes a few minutes for ~44k stations.
"""
import json, sys, time, threading, collections
from concurrent.futures import ThreadPoolExecutor
import requests, urllib3

urllib3.disable_warnings()
ORIGIN = "https://www.gridspot.co"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
WORKERS = 200
TIMEOUT = (6, 10)  # connect, read
AUDIO = ("audio/", "application/ogg", "video/mp2t", "application/octet-stream",
         "video/mp4", "application/aac")
HLS_CT = ("mpegurl", "x-mpegurl")
RETRY = {"timeout", "connect", "read", "empty", "error"}

local = threading.local()


def session():
    if not hasattr(local, "s"):
        s = requests.Session()
        s.headers.update({"User-Agent": UA, "Origin": ORIGIN, "Icy-MetaData": "0"})
        s.max_redirects = 6
        local.s = s
    return local.s


def probe(u, hls):
    """u is the stream URL without its scheme. Returns a reason string; "ok" if playable."""
    try:
        r = session().get("https://" + u, stream=True, timeout=TIMEOUT)
    except requests.exceptions.SSLError:
        return "tls"
    except requests.exceptions.Timeout:
        return "timeout"
    except requests.exceptions.ConnectionError:
        return "connect"
    except Exception:
        return "error"
    try:
        if any(h.url.startswith("http://") for h in r.history) or r.url.startswith("http://"):
            return "redirect-http"
        if r.status_code != 200:
            return "http-%d" % r.status_code
        ct = (r.headers.get("Content-Type") or "").lower()
        head = b""
        deadline = time.time() + 10
        for chunk in r.iter_content(2048):
            head += chunk
            if len(head) >= 2048 or time.time() > deadline:
                break
        if not head:
            return "empty"
        is_hls = head.lstrip().startswith(b"#EXTM3U") or any(x in ct for x in HLS_CT)
        if is_hls:
            if not head.lstrip().startswith(b"#EXTM3U"):
                return "bad-playlist"
            acao = r.headers.get("Access-Control-Allow-Origin", "")
            if acao not in ("*", ORIGIN):
                return "hls-no-cors"
            return "ok"
        if ct.startswith("text/html") or head.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
            return "html"
        if ct.startswith(AUDIO) or ct == "":
            return "ok"
        # .pls / .m3u playlists and the like: the <audio> element can't play them
        return "type:" + ct.split(";")[0]
    except Exception:
        return "read"
    finally:
        r.close()


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    data = json.load(open("data.json", encoding="utf-8"))
    st = data["stations"][:limit] if limit else data["stations"]
    res = [None] * len(st)
    done = [0]
    lock = threading.Lock()
    t0 = time.time()

    def work(k):
        res[k] = probe(st[k][1], st[k][13])
        with lock:
            done[0] += 1
            if done[0] % 1000 == 0:
                print("  %d/%d  %.0fs" % (done[0], len(st), time.time() - t0), file=sys.stderr)

    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, range(len(st))))

    # a lot of servers just choke when hit 200 at a time; give anything that
    # looks transient a second, slower, more patient try
    global TIMEOUT
    TIMEOUT = (12, 20)
    again = [k for k, r in enumerate(res) if r in RETRY or r.startswith("http-5")]
    print("retrying %d transient failures" % len(again), file=sys.stderr)
    with ThreadPoolExecutor(WORKERS // 4) as ex:
        list(ex.map(work, again))

    why = collections.Counter(res)
    print("probed %d in %.0fs" % (len(st), time.time() - t0))
    for k, v in why.most_common():
        print("  %-22s %d" % (k, v))
    kept = []
    print("  (%d of the kept were http-only and work over https too)"
          % sum(1 for r, s in zip(res, st) if r == "ok" and not s[2]))
    for r, s in zip(res, st):
        if r == "ok":
            s[2] = 1  # reachable over https now, whatever it was registered as
            kept.append(s)
    print("kept %d of %d" % (len(kept), len(st)))
    if limit:
        print("(sample run, data.json not written)")
        return

    # re-pack the lookup tables so they only hold values still in use
    def repack(name, col, multi=False):
        old = data[name]
        used = sorted({x for s in kept for x in (s[col] if multi else [s[col]]) if x >= 0})
        remap = {o: n for n, o in enumerate(used)}
        data[name] = [old[o] for o in used]
        for s in kept:
            s[col] = [remap[x] for x in s[col]] if multi else remap.get(s[col], -1)

    data["stations"] = kept
    repack("countries", 5)
    repack("states", 6)
    repack("langs", 7, True)
    repack("tags", 8, True)
    repack("codecs", 9)
    data["probed"] = time.strftime("%Y-%m-%d")
    js = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    open("data.json", "w", encoding="utf-8").write(js)
    print("wrote data.json: %d stations, %d countries (%.2f MB)"
          % (len(kept), len(data["countries"]), len(js.encode()) / 1e6))


if __name__ == "__main__":
    main()
