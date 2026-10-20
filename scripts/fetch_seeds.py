"""Download and unpack the sdists listed in PINS into <workdir>/raw/<name>/ (nothing from them is executed).
Writes seeds/SOURCES.json with the exact file, URL and sha256 of everything fetched (no local paths).
usage: python scripts/fetch_seeds.py <workdir>"""
import json
import sys
from pathlib import Path

from miniagent.taskgen.pypi import download, release_info, safe_extract

PINS = {"parse": "1.22.3", "toposort": "1.10", "xmltodict": "1.0.4", "pytimeparse": "1.1.10", "inflection": "0.5.1",
        "schema": "0.7.8", "ordered-set": "4.1.0", "sortedcontainers": "2.4.0", "cachetools": "7.2.3", "toolz": "1.2.0",
        "boltons": "26.2.0", "tabulate": "0.10.0", "jsonpointer": "3.2.1", "sqlparse": "0.6.0", "decorator": "5.3.1",
        "six": "1.17.0", "termcolor": "3.3.0", "colorama": "0.4.6", "more-itertools": "11.2.1", "jmespath": "1.1.0"}

work = Path(sys.argv[1])
sources = []
for name, version in PINS.items():
    info = release_info(name, version)
    archive = download(info, work / "downloads")
    root = safe_extract(archive, work / "raw" / name)
    sources.append(info)
    print(f"{name:18} {version:9} {info['size'] / 1024:6.0f} KB  sha256 {info['sha256'][:12]}…  ok")
Path("seeds").mkdir(exist_ok=True)
Path("seeds/SOURCES.json").write_text(json.dumps(sources, indent=2))
