import osmium_helper
import requests
from schema import Schema
from tqdm import tqdm
import os

# Download latest Germany OSM PBF file from Geofabrik
def download_osm_pbf(url, output_path):
    if os.path.exists(output_path):
        print(f"{output_path} already exists, skipping download.")
        return
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(output_path, "wb") as f, tqdm(
            desc="Downloading", total=total, unit="B", unit_scale=True
        ) as pbar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))




# Main script
if __name__ == "__main__":
    PBF_URL = "https://download.geofabrik.de/europe/germany-latest.osm.pbf"
    PBF_FILE =  "germany-latest.osm.pbf"
    OUTPUT_JSON = "germany_maxspeed.json"

    download_osm_pbf(PBF_URL, PBF_FILE)

    PBF_FILE = "munich-latest.osm.pbf"

    print("Parsing PBF...")
    handler = osmium_helper.SpeedHandler()
    handler.apply_file_hardcore(PBF_FILE)

    print(f"Extracted {len(handler.roads)} roads with maxspeed.")
    db = Schema()
    db.setup_tables()
    db.insert_roads(handler.roads)

    print("Done.")
