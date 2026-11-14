"""Build courts.json: every basketball court in an OpenStreetMap extract.

Run by .github/workflows/courts-data.yml once a week, so the Court Finder page
never has to ask the (overloaded) public Overpass servers anything.

Usage: python build_courts.py pitches.osm.pbf courts.json
The input should already be filtered to leisure=pitch with
`osmium tags-filter netherlands.osm.pbf nwr/leisure=pitch`, which keeps the
nodes/ways those pitches are made of, so we can compute their centres here.
"""
import json
import sys
from datetime import datetime, timezone

import osmium

KEEP = ["name", "surface", "hoops", "hoops:nets", "hoops:height",
        "lit", "indoor", "covered", "access", "sport"]


def is_basketball(tags):
    if tags.get("leisure") != "pitch":
        return False
    return "basketball" in [s.strip() for s in tags.get("sport", "").split(";")]


def slim(tags):
    return {k: tags[k] for k in KEEP if k in tags}


class Courts(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.way_centres = {}  # way id -> (lat, lon), for relation members
        self.courts = []

    def node(self, n):
        if is_basketball(n.tags) and n.location.valid():
            self.courts.append([round(n.location.lat, 6), round(n.location.lon, 6),
                                f"node/{n.id}", slim(n.tags)])

    def way(self, w):
        pts = [(nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]  # closed way: don't count the first corner twice
        if not pts:
            return
        c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        self.way_centres[w.id] = c
        if is_basketball(w.tags):
            self.courts.append([round(c[0], 6), round(c[1], 6), f"way/{w.id}", slim(w.tags)])

    def relation(self, r):
        if not is_basketball(r.tags):
            return
        cs = [self.way_centres[m.ref] for m in r.members if m.type == "w" and m.ref in self.way_centres]
        if cs:
            self.courts.append([round(sum(c[0] for c in cs) / len(cs), 6),
                                round(sum(c[1] for c in cs) / len(cs), 6),
                                f"relation/{r.id}", slim(r.tags)])


def main(src, dst, min_courts=100):
    h = Courts()
    h.apply_file(src, locations=True)
    if len(h.courts) < min_courts:  # e.g. a broken download: keep last week's good file
        sys.exit(f"Only {len(h.courts)} courts found; refusing to overwrite {dst}.")
    h.courts.sort(key=lambda c: (c[0], c[1]))
    try:  # nothing changed in OSM since last week → don't make a pointless commit
        with open(dst, encoding="utf-8") as f:
            if json.load(f).get("courts") == h.courts:
                print(f"{len(h.courts)} courts, unchanged since last run.")
                return
    except (FileNotFoundError, ValueError):
        pass
    out = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "source": "© OpenStreetMap contributors (ODbL), extract by Geofabrik",
        "courts": h.courts,
    }
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(h.courts)} basketball courts written to {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 100)
