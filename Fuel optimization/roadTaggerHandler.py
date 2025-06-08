import osmium
import os
import shutil
import uuid

class RoadTaggerHandler(osmium.SimpleHandler):
    def __init__(self, writer):
        super().__init__()
        self.writer = writer
        self.counter = 1

    def way(self, w):
        if not w.tags.get('highway'):
            return

        road_id = f"road_{self.counter:05d}"
        self.counter += 1

        # Manually create a mutable way and copy fields
        new_way = osmium.osm.mutable.Way()
        new_way.id = w.id
        new_way.version = w.version
        new_way.visible = w.visible
        new_way.nodes = w.nodes

        # Create a new tag list manually
        tags = [(tag.k, tag.v) for tag in w.tags]
        tags.append(("road_id", road_id))
        new_way.tags = tags  # pass as list of tuples

        self.writer.add_way(new_way)


def process_osm(input_file: str, output_file: str):
    temp_dir = os.path.dirname(output_file) or '.'
    temp_output = os.path.join(temp_dir, f"{uuid.uuid4().hex}.osm.pbf")

    try:
        # Create writer with node locations enabled
        writer = osmium.SimpleWriter(temp_output)
        
        # First pass: Copy all nodes with locations
        node_handler = osmium.SimpleHandler()
        def copy_node(n):
            new_node = osmium.osm.mutable.Node(n)
            writer.add_node(new_node)
        node_handler.node = copy_node
        node_handler.apply_file(input_file, locations=True)
        
        # Second pass: Process ways with our tagger
        way_handler = RoadTaggerHandler(writer)
        way_handler.apply_file(input_file, locations=True)
        
        writer.close()

        if os.path.exists(output_file):
            os.remove(output_file)
        shutil.move(temp_output, output_file)

        print(f"✅ Successfully wrote modified data to: {output_file}")
    except Exception as e:
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except Exception:
                pass
        print(f"❌ Error processing OSM file: {str(e)}")
        raise

if __name__ == "__main__":
    input_path = os.path.abspath("moscow.osm.pbf")
    output_path = os.path.abspath("moscow_tagged.osm.pbf")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    process_osm(input_path, output_path)
