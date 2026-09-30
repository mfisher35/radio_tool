#!/bin/sh
# Re-download the station list and rebuild radio.html.
# Takes about a minute; the Radio Browser API is paginated 4,000 at a time.
set -e
cd "$(dirname "$0")"
python3 fetch_stations.py
python3 build_data.py
python3 assemble.py ../radio.html
echo "Done. Open ../radio.html"
