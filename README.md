# Radio Atlas

A single-file internet radio browser: **33,805 stations from 210 countries**, searchable,
playable, shufflable, with a favorites list you own.

Open `radio.html` in a browser. That's the whole install — no server, no build step, no
network call except the audio streams themselves and one visitor-count request.

```sh
open radio.html
```

## What it does

- **Search** — one box over station name, country, region, genre and language. Multiple
  words are ANDed (`bbc radio`, `jazz france`). Results update as you type.
- **Filter** — country, language, genre chips, minimum bitrate.
- **Play** — click any row. The bottom bar shows what's on air, bitrate, codec, and links
  to the station's own site.
- **Random** — the `Random` button (or `R`) picks from *whatever list is currently on
  screen*. So it shuffles all 34k by default, but filter to `jazz` + `Italy` first and it
  shuffles only those.
- **Favorites** — star any station. `Favorites` (or `V`) switches the list to just those,
  and `Random` then picks only from your favorites. Stored in the browser, and
  exportable/importable as JSON so you can back them up or move them to another machine.

- **Car & headset controls** — next/previous on a car stereo, Bluetooth headset, lock
  screen or keyboard media keys work too (via the Media Session API). In the favorites
  view they step through your favorites in order, wrapping around and skipping dead
  streams. Anywhere else, next picks a random station from the current list and previous
  goes back through the stations you've actually played.

- **Visitor counter** — the player bar shows how many unique visitors the page has had.
  The first time a browser opens the page it increments a shared count at
  [Abacus](https://abacus.jasoncameron.dev/) (a free counter API; namespace
  `radio-atlas-k7q2`), and sets a `localStorage` flag so later visits only read the
  number. Nothing about the visitor is sent beyond the request itself. If the service is
  unreachable the counter just stays hidden.

### Keyboard

| Key | Action |
| --- | --- |
| `/` | focus search |
| `Space` | play / pause |
| `R` | random station from the current list |
| `N` / `P` | next / previous station (in order in favorites view; otherwise next is random, previous goes back) |
| `F` | favorite the playing station |
| `V` | toggle favorites view |
| `Esc` | clear focus / dismiss |

## Every station plays over HTTPS

The page works opened from disk or hosted on an `https://` site. A page served over
HTTPS can't play plain `http://` streams, because the browser blocks them as mixed
content. So at build time every stream was connected to over HTTPS and kept only if it
actually sent back audio. Of the stations registered as http-only, about 8,000 turned out
to serve the same stream over HTTPS too, so they're kept with an `https://` URL.

Favorites live in the page's `localStorage`, which is tied to where the page is opened
from (a different file path or a different site gets a fresh, empty store). Use **Export
favorites** before moving it.

## Dead streams

Internet radio rots constantly. When a stream refuses to play, the app marks it, dims it
in the list, and offers to jump to another. **Hide streams that failed here** (on by
default) keeps them out of your results and out of the random pool. That list is local to
you — nothing is reported anywhere.

Stations flagged broken upstream, and every stream that wouldn't connect when the list
was built (see below), are already excluded. Still, a stream that worked this morning can
be gone tonight.

## Rebuilding the station list

Data comes from [Radio Browser](https://www.radio-browser.info/), a community-run open
database (public domain). To pull a fresh copy:

```sh
build/refresh.sh
```

That runs four steps, which you can also run individually from `build/`. It takes about
half an hour, almost all of it spent probing streams:

| Script | Does |
| --- | --- |
| `fetch_stations.py` | pages the API into `data.json`'s raw source, `stations.json` (~71 MB, 59,828 rows) |
| `build_data.py` | dedupes and dictionary-compresses it to `data.json` (~6 MB) |
| `probe_streams.py` | connects to every stream over HTTPS and drops the ones that won't play (rewrites `data.json`, ~4.8 MB) |
| `assemble.py` | inlines `data.json` into `template.html` → `radio.html` |

Edit the UI in `build/template.html`, not in `radio.html` — the latter is generated.

### How 59,828 rows become 33,805

Deduped twice: first by stream URL, then by station name within a country, each time
keeping the most-played copy. The same station is often registered many times over.
That leaves 43,957. Then `probe_streams.py` keeps only the streams a browser on an
HTTPS page could really play: reachable over `https://` with a valid certificate, no
redirect back to `http://`, a 200 response with audio in it rather than an HTML page,
and, for HLS, CORS headers (outside Safari, hls.js fetches the playlist itself). Anything
that times out or won't connect gets a second, slower try before it's dropped. That
removes about 10,000 more: mostly bad or missing certificates on http-only servers,
timeouts, and dead hosts.

Each row is then dictionary-encoded — countries, languages, genres and codecs are stored
once and referenced by integer — which is what gets 71 MB down to 6 MB.

Bitrates reported in bits/sec are converted to kbps, and anything still above CD rate is
treated as unknown.

## Notes

- Station artwork is deliberately not used. Favicon URLs would have added megabytes and
  thousands of third-party image requests; the colored monogram tiles are derived from the
  station name instead.
- HLS (`.m3u8`) streams work natively in Safari; elsewhere hls.js is lazy-loaded from a CDN
  the first time one is played.
- The list renders virtually, so scrolling 34,000 rows keeps about 22 in the DOM.
