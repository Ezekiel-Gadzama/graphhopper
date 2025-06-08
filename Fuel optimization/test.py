import osmium

class RoadExtractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.count = 0

    def way(self, w):
        if 'highway' in w.tags:
            print(f"✅ Road ID: {w.id}, Tags: {dict(w.tags)}")
            try:
                coords = [(n.lon, n.lat) for n in w.nodes]
                print(f"Coordinates: {coords[:5]} ...")  # Only show a few
            except Exception as e:
                print(f"⚠️ Error extracting coords for way {w.id}: {e}")
            print()
            self.count += 1
            if self.count >= 5:
                raise StopIteration  # Stop after 5 roads for a quick test

if __name__ == "__main__":
    handler = RoadExtractor()
    handler.apply_file("moscow_tagged.osm.pbf", locations=True)  # <- Removed idx
