import sys
import requests
import os
import os.path
import csv
import shutil
from random import random
from time import sleep
from tqdm import tqdm
import glob


# Loading custom libraries
libs_path = os.path.join("..", "..", "backend", "libs")
sys.path.append(libs_path)
import QuadKey.quadkey as quadkey

from .utils import QuadKeyToTileXY, find_quadkey, find_files


def crawler(root_class, zoom, image_database, database):
    if not (os.path.exists(image_database)):
        print("Creating a new image database\t\t[done]")
        os.mkdir(image_database)

    tile_dir = os.path.join(image_database, str(zoom))
    if not (os.path.exists(tile_dir)):
        print("Creating a directory for zoom level {}\t[done]".format(zoom))
        os.mkdir(tile_dir)

    root_path = os.path.join(database, root_class)
    # print("Acquiring OSM data\t\t\t[done]")
    csv_files = find_files(path=root_path, suffix="csv")

    for csv_file in csv_files:
        csv_file = os.path.join(csv_file)

        with open(csv_file, "rt") as input_file:
            reader = csv.reader(input_file, delimiter="\t")
            download = False
            for row in tqdm(reader, desc="downloading tiles"):
                pixel = quadkey.TileSystem.geo_to_pixel(
                    (float(row[0]), float(row[1])), zoom
                )
                for x in range(-2, 3):
                    for y in range(-2, 3):
                        pixel_quadkey = find_quadkey(pixel, x, y, zoom)
                        tileCache = os.path.join(tile_dir, pixel_quadkey[-3:])
                        if not (os.path.exists(tileCache)):
                            os.mkdir(tileCache)
                        tile_path = "{}/{}.jpg".format(tileCache, pixel_quadkey)
                        if os.path.exists(tile_path):
                            pass
                        else:
                            # TODO: get subdomain using random.choice(bing_subdomains)
                            xx, yy, zz = QuadKeyToTileXY(pixel_quadkey)
                            # tile_url = f"https://khms1.googleapis.com/kh?v=942&hl=en-US&x={xx}&y={yy}&z={zz}"
                            tile_url = (
                                f"http://mt1.google.com/vt/lyrs=s&x={xx}&y={yy}&z={zz}"
                            )
                            response = requests.get(tile_url, stream=True)
                            with open(tile_path, "wb") as new_tile:
                                shutil.copyfileobj(response.raw, new_tile)
                            del response
                            download = True
            if download:
                sleep(random() * 3)
