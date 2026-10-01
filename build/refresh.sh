#!/bin/sh
# Re-download the station list and rebuild radio.html.
# Takes about half an hour: a minute to page the Radio Browser API, the rest
# to connect to every stream and drop the ones that will not play on https.
set -e
cd "$(dirname "$0")"
python3 fetch_stations.py
python3 build_data.py
python3 probe_streams.py
python3 assemble.py ../radio.html
echo "Done. Open ../radio.html"
