# Radio Atlas

A single-file internet radio browser: **43,957 stations from 218 countries**, searchable,
playable, shufflable, with a favorites list you own.

Open `radio.html` in a browser. That's the whole install — no server, no build step, no
network call except the audio streams themselves.

```sh
open radio.html
```

## What it does

- **Search** — one box over station name, country, region, genre and language. Multiple
  words are ANDed (`bbc radio`, `jazz france`). Results update as you type.
- **Filter** — country, language, genre chips, minimum bitrate, HTTPS-only.
- **Play** — click any row. The bottom bar shows what's on air, bitrate, codec, and links
  to the station's own site.
- **Random** — the `Random` button (or `R`) picks from *whatever list is currently on
  screen*. So it shuffles all 44k by default, but filter to `jazz` + `Italy` first and it
  shuffles only those.
- **Favorites** — star any station. `Favorites` (or `V`) switches the list to just those,
  and `Random` then picks only from your favorites. Stored in the browser, and
  exportable/importable as JSON so you can back them up or move them to another machine.

### Keyboard

| Key | Action |
| --- | --- |
| `/` | focus search |
| `Space` | play / pause |
| `R` | random station from the current list |
| `F` | favorite the playing station |
| `V` | toggle favorites view |
| `Esc` | clear focus / dismiss |

## Why it's a local file and not a hosted page

About 38% of these stations only stream over plain `http://`. A page served over HTTPS
cannot play them — the browser blocks them as mixed content, and you'd silently lose more
than a third of the list. Opened from disk, every stream is reachable.

Favorites live in this file's `localStorage`, so keep `radio.html` where it is (moving it
changes the origin and the browser hands you a fresh, empty store). Use **Export
favorites** before moving it.

## Dead streams

Internet radio rots constantly. When a stream refuses to play, the app marks it, dims it
in the list, and offers to jump to another. **Hide streams that failed here** (on by
default) keeps them out of your results and out of the random pool. That list is local to
you — nothing is reported anywhere.

Stations already flagged broken upstream were excluded at build time, but a stream that
worked this morning can still be gone tonight.

## Rebuilding the station list

Data comes from [Radio Browser](https://www.radio-browser.info/), a community-run open
database (public domain). To pull a fresh copy:

```sh
build/refresh.sh
```

That runs three steps, which you can also run individually from `build/`:

| Script | Does |
| --- | --- |
| `fetch_stations.py` | pages the API into `data.json`'s raw source, `stations.json` (~71 MB, 59,828 rows) |
| `build_data.py` | dedupes and dictionary-compresses it to `data.json` (~6 MB) |
| `assemble.py` | inlines `data.json` into `template.html` → `radio.html` |

Edit the UI in `build/template.html`, not in `radio.html` — the latter is generated.

### How 59,828 rows become 43,957

Deduped twice: first by stream URL, then by station name within a country, each time
keeping the most-played copy. The same station is often registered many times over.
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
- The list renders virtually, so scrolling 44,000 rows keeps about 22 in the DOM.
