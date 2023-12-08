# coding: utf-8

import sys
from numpy import random
import overpy
from overpy.exception import OverpassTooManyRequests, OverpassGatewayTimeout
import os
import shapely.geometry
import shapely.wkt
import shapely.ops
import geojson
import time
from shapely.geometry import shape
from http.client import IncompleteRead

# from utils import load_config ,read_query, logger
import time
import pprint

prettyprinter = pprint.PrettyPrinter(indent=4)
summery = {}

# crawling
# count = 0
def decode(way, db, name, local_db):
    print(f"crawling {way.id}")
    # check f"{str(way.id)}.GeoJSON" exists in local_db
    if os.path.exists(os.path.join(local_db, name, str(way.id) + ".GeoJSON")):
        print(f"{name}/{way.id}.GeoJSON already exists in {local_db}")
        # copy f"{str(way.id)}.GeoJSON" from local_db to db
        if not os.path.exists(os.path.join(db, name, str(way.id) + ".GeoJSON")):
            os.system(
                f"copy {os.path.join(local_db, name, str(way.id) + '.GeoJSON')} {os.path.join(db, name, str(way.id) + '.GeoJSON')}"
            )
            # copy f"{str(way.id)}.csv" from local_db to db
            os.system(
                f"copy {os.path.join(local_db, name, str(way.id) + '.csv')} {os.path.join(db, name, str(way.id) + '.csv')}"
            )

    category = str(way.tags.get(name))
    category_dir = os.path.join(db, name, str(way.id))
    # print(f"saving into {category_dir}")
    #
    # if not os.path.exists(f"{category_dir}.csv"):
    #     with open("%s.csv" % (category_dir), "wt") as text_file:
    #         for node in way.get_nodes(resolve_missing=True):
    #             text_file.write("%0.7f\t%0.7f\n" % (node.lat, node.lon))
    # else:
    #     print(f"{category_dir}.csv already exists")

    if not os.path.exists(f"{category_dir}.GeoJSON"):
        if not os.path.exists(f"{category_dir}.csv"):
            with open("%s.GeoJSON" % (category_dir), "wt") as geo_file:
                with open("%s.csv" % (category_dir), "wt") as csv_file:
                    rawNodes = []
                    while True:
                        try:
                            for node in way.get_nodes(resolve_missing=True):
                                csv_file.write("%0.7f\t%0.7f\n" % (node.lat, node.lon))
                                rawNodes.append((node.lon, node.lat))
                            try:
                                geom = shapely.geometry.Polygon(rawNodes)
                                tags = way.tags
                                tags["wayOSMId"] = way.id

                                features = []
                                features.append(
                                    geojson.Feature(geometry=geom, properties=tags)
                                )
                                featureCollection = geojson.FeatureCollection(features)
                                # print(featureCollection)
                                geo_file.write(geojson.dumps(featureCollection))
                                if category in summery:
                                    summery[category] += 1
                                else:
                                    summery[category] = 1
                                # count += 1
                            except Exception as expt:
                                print(f"{category_dir}:{expt}")
                        except OverpassTooManyRequests:
                            time.sleep(2)
                            print("OverpassTooManyRequests, retrying...")
                            continue
                        except OverpassGatewayTimeout:
                            time.sleep(10)
                            print("OverpassGatewayTimeout, retrying...")
                            continue
                        except IncompleteRead:
                            time.sleep(5)
                            print("IncompleteRead, retrying...")
                            continue
                        break
                    return 1
    else:
        print(f"{category_dir}.GeoJSON/.csv already exists")
        return 0

def get_time(hours):
    minutes = hours * 60
    # Separate the integer part of the minutes and the decimal part (seconds)
    whole_minutes = int(minutes)
    seconds = (minutes - whole_minutes) * 60
    return whole_minutes, seconds

def crawler(query, db, name, local_db):
    api = overpy.Overpass()
    api.default_max_retry_count = 10  # default is 5
    api.default_retry_timeout = 15  # seconds
    result = api.query(query)

    # create osm database folder if not exists
    output_dir = os.path.join(db, name)
    if os.path.exists(output_dir) == False:
        print("Creating a new local OSM database\t[done]")
        os.makedirs(output_dir)
    print(f"{len(result.ways)} file/s will be saved into {output_dir}")
    mins, secs = get_time(len(result.ways) * 3 / 3600)
    print(f"Estimated time: {mins} minutes and {secs:.2f} seconds")
    for way in result.ways:
        if way.id == 810540712:
            print(">>>>> 810540712 occurs in result.ways")
            continue        
        ret = decode(way, db, name, local_db)
