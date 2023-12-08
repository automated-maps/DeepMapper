import os
conda_env = os.environ.get('CONDA_PREFIX')
if conda_env.split("\\")[-1]!="tf-geo":
    print("Activate tf-geo environment first.")
    exit(0)

import sys
sys.path.append("C:\Program Files\GDAL\gdalplugins")
import glob
import time
import json
import shutil
import uuid
import subprocess
import folium
import webcolors
import random


import geopandas as gpd
from folium.plugins import *


from flask import Flask, render_template, request, jsonify, flash, redirect, send_file, Response
from flask_assets import Environment, Bundle
from flask_cors import CORS


from crawlers.osm import crawler as osm_crawler
from crawlers.google import crawler as google_crawler
from crawlers.utils import load_config, build_query, bcolors, filter_coco_image
from crawlers.build_dataset import coco_builder, osm_gan_data_builder
from osmgan.osmgan import change_detection
from polygan.polygan import applyPerpendicularDistance
from polymerge.polymerge import createCollisionsGraph, PolyMerge
from changeset.builder import buildChangeSet

async_mode = None

app = Flask(__name__)
assets = Environment(app)

js = Bundle('js/leaflet.js', output='gen/packed.js')
css = Bundle('css/leaflet.css', output='gen/packed.css')
assets.register('js_all', js)
assets.register('css_all', css)

session_id = str(uuid.uuid4())
print("[INFO] Session ID: {}".format(session_id))

config_file = "./config/config.yaml"
config = load_config(config_file)

app.secret_key = f"{config['API']['token']}".encode('utf-8')
CORS(app)

cache = "cache.json"
version = "v1"

ROOT = config["data_dir"]

session_dir = os.path.join(ROOT, session_id)
vector_db = os.path.join(session_dir, config["osm_database"])
# socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins="*")

# Define a function to generate random RGB colors
def random_color():
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)
    return (red, green, blue)

def check_and_write_cache(idx, coords):
    data = {}
    if os.path.exists(cache):
        with open(cache, "r") as f:
            data = json.load(f)
    if coords in list(data.values()):
        return True, list(data.keys())[list(data.values()).index(coords)]
    else:
        data[idx] = coords
        with open(cache, "w") as f:
            json.dump(data, f, indent=4)
        return False, idx


@app.route("/")
def index():
    os.makedirs(ROOT, exist_ok=True)
    return render_template("index.html")


@app.route(f"/api/{version}/resources/settings", methods=["GET"])
def get_settings():
    return jsonify(config)


@app.route(f"/api/{version}/resources/clean", methods=["GET"])
def clean():
    data = {}
    with open("cache.json", "w") as f:
        json.dump(data, f)
    if os.path.isdir(ROOT):
        dirs = os.listdir(ROOT)
        print(f"{bcolors.FAIL}")
        for _dir in dirs:
            print(f"Removing {os.path.join(ROOT, _dir)}...")
        print(f"{bcolors.ENDC}")
        shutil.rmtree(ROOT, ignore_errors=True)
        return jsonify(
            {"message": "Cleaning up...", "_dirs": dirs, "status": "success"}
        )
    else:
        return jsonify({"message": "Nothing to clean...", "status": "success"})

@app.route("/dataset")
def index_2():
    session_id = str(uuid.uuid4())
    print("[INFO] Session ID: {}".format(session_id))
    os.makedirs(ROOT, exist_ok=True)
    return render_template("index_2.html")


@app.route("/make_dataset", methods=["POST"])
def make_dataset(session_id=session_id):
    session_id = str(uuid.uuid4())
    print("[INFO] Session ID: {}".format(session_id))
    message_queue = []
    # Obtain the polygon coordinates from the form data
    polygon_coords = request.form.get("boxbounds")
    polygon_coords = polygon_coords.replace('"', "")
    print(f"{bcolors.OKBLUE}[INFO] Polygon coordinates: {polygon_coords}{bcolors.ENDC}")
    message_queue.append(f"[INFO] Session ID: {session_id}")
    message_queue.append(f"[INFO] Polygon coordinates: {polygon_coords}")

    # Check for "0.000000,0.000000,0.000000,0.000000"
    if polygon_coords == "0.000000,0.000000,0.000000,0.000000":
        print(f"{bcolors.FAIL}[ERROR] Invalid polygon coordinates{bcolors.ENDC}")
        return redirect("/")
    else:
        # Build the overpass query
        overpy_query = build_query(polygon_coords)
        name = config["name"]
        session_dir = os.path.join(ROOT, session_id)
        local_db = config["local_db"]
        vector_db = os.path.join(session_dir, config["osm_database"])
        os.makedirs(session_dir, exist_ok=True)
        # ask yes/no to continue
        inp = input("Do you want to continue? [y/n]: ")
        if inp == "n":
            return redirect("/")      

        # OSM crawler
        print(f"{bcolors.OKGREEN}")
        # TODO:
        # if osm node exists on local_db then copy it to vector_db
        # else download it from OSM and copy it to vector_db
        osm_crawler(overpy_query, vector_db, name, local_db)
        print(f"{bcolors.ENDC}")
        flash("OSM crawler finished")
        message_queue.append("[INFO] OSM crawler finished")

        # copy content of the vector_db to local_db
        print(f"{bcolors.OKGREEN}")
        print(f"[INFO] Copying {vector_db} to {local_db}")
        message_queue.append(f"[INFO] Copying {vector_db} to {local_db}")
        for file in os.listdir(os.path.join(vector_db, name)):
            shutil.copy(
                os.path.join(vector_db, name, file), os.path.join(local_db, name)
            )
        print(f"{bcolors.ENDC}")

        # Google crawler
        zoom = config["zoom"]
        image_db = os.path.join(session_dir, config["image_database"])
        print(f"{bcolors.OKBLUE}")
        google_crawler(name, zoom, image_db, vector_db)
        message_queue.append("[INFO] Google crawler finished")
        print(f"{bcolors.ENDC}")

        # Data Builder
        coco_dataset = os.path.join(session_dir, config["dataset"])
        os.makedirs(coco_dataset, exist_ok=True)
        print(f"{bcolors.FAIL}")
        coco_builder(local_db, image_db, coco_dataset, zoom)
        message_queue.append("[INFO] Data Builder finished")
        print(f"{bcolors.ENDC}")

        # filter out images with no annotations
        print(f"{bcolors.WARNING}")
        filter_coco_image(coco_dataset)
        message_queue.append("[INFO] Filtered out images with no annotations")
        print(f"{bcolors.ENDC}")

        # OSM-GAN dataset builder
        osm_gan_path = os.path.join(session_dir, config["osm_gan"])
        osm_gan_dataset = os.path.join(osm_gan_path, "test")
        os.makedirs(osm_gan_dataset, exist_ok=True)
        print(f"{bcolors.OKCYAN}")
        osm_gan_data_builder(coco_dataset, osm_gan_dataset)
        message_queue.append("[INFO] OSM-GAN dataset builder finished")
        print(f"{bcolors.ENDC}")
        
        # OSM-GAN Prediction
        # env = config["prediction"]["conda_env"]
        # name = config["prediction"]["model_name"]
        # model = config["prediction"]["model_func"]
        # direction = config["prediction"]["direction"]
        # num_test = len(os.listdir(osm_gan_dataset))
        # print(
        #     f"{bcolors.FAIL}python test.py --dataroot {osm_gan_dataset} --name {name} --model {model} --direction {direction}  --num_test {num_test}{bcolors.ENDC}"
        # )
        # os.chdir("./libs/pix2pix")
        # abs_osm_gan_path = os.path.join("..", "..", osm_gan_path)
        # subprocess.call(
        #     f"python test.py --dataroot {abs_osm_gan_path} --name {name} --model {model} --direction {direction}  --num_test {num_test}",
        #     shell=True,
        # )
        # message_queue.append("[INFO] OSM-GAN Prediction finished")
        # os.chdir("../../")
        # pix2pix_result_dir = f"./libs/pix2pix/results/{name}/test_latest/images"
        # result_path = os.path.join(
        #     osm_gan_path, "results", name, "test_latest", "images"
        # )
        # shutil.move(pix2pix_result_dir, result_path)
        # message_queue.append("[INFO] OSM-GAN Predictions moved to results folder")
        
        
        return jsonify({"message_queue": message_queue})



@app.route('/stream')
def stream():
    def event_stream():
        for event in process_polygon():
            if event == "redirect":
                yield "data: redirect\n\n"  # Signal to redirect
            else:
                yield "data: " + event + "\n\n"  # Send event data

    return Response(event_stream(), mimetype="text/event-stream")

# @app.route("/process_polygon", methods=["POST"])
# def process_polygon(session_id=session_id):
#     time.sleep(1)
#     print("[INFO] data processing started.")
#     yield "[INFO] pre processing completed."
#     time.sleep(2)
#     print("[INFO] data processing started.")
#     yield "[INFO] data processing completed."
#     time.sleep(2)
#     print("[INFO] post processing started.")
#     yield "[INFO] post processing completed."
    # time.sleep(3)
    # yield "redirect"  # Signal to redirect


@app.route("/process_polygon", methods=["POST"])
def process_polygon(session_id=session_id):
    message_queue = []
    # Obtain the polygon coordinates from the form data
    polygon_coords = request.form.get("boxbounds")
    polygon_coords = polygon_coords.replace('"', "")
    print(f"{bcolors.OKBLUE}[INFO] Polygon coordinates: {polygon_coords}{bcolors.ENDC}")
    message_queue.append(f"[INFO] Session ID: {session_id}")
    message_queue.append(f"[INFO] Polygon coordinates: {polygon_coords}")
    # yield f"session created: {session_id}"
    # Check for "0.000000,0.000000,0.000000,0.000000"
    if polygon_coords == "0.000000,0.000000,0.000000,0.000000":
        print(f"{bcolors.FAIL}[ERROR] Invalid polygon coordinates{bcolors.ENDC}")
        return redirect("/")
    else:
        # Build the overpass query
        overpy_query = build_query(polygon_coords)
        name = config["name"]
        session_dir = os.path.join(ROOT, session_id)
        local_db = config["local_db"]
        vector_db = os.path.join(session_dir, config["osm_database"])
        os.makedirs(session_dir, exist_ok=True)

        # OSM crawler
        print(f"{bcolors.OKGREEN}")
        # TODO:
        # if osm node exists on local_db then copy it to vector_db
        # else download it from OSM and copy it to vector_db
        osm_crawler(overpy_query, vector_db, name, local_db)
        print(f"{bcolors.ENDC}")
        message_queue.append("[INFO] OSM crawler finished")

        # copy content of the vector_db to local_db
        print(f"{bcolors.OKGREEN}")
        print(f"[INFO] Copying {vector_db} to {local_db}")
        message_queue.append(f"[INFO] Copying {vector_db} to {local_db}")
        for file in os.listdir(os.path.join(vector_db, name)):
            shutil.copy(
                os.path.join(vector_db, name, file), os.path.join(local_db, name)
            )
        print(f"{bcolors.ENDC}")

        # Google crawler
        zoom = config["zoom"]
        image_db = os.path.join(session_dir, config["image_database"])
        print(f"{bcolors.OKBLUE}")
        google_crawler(name, zoom, image_db, vector_db)
        message_queue.append("[INFO] Google crawler finished")
        print(f"{bcolors.ENDC}")


        # ask to continue
        inp = input("Do you want to continue? [y/n]: ")
        if inp == "n":
            return {"messages" : message_queue}
            

        

        # Data Builder
        coco_dataset = os.path.join(session_dir, config["dataset"])
        os.makedirs(coco_dataset, exist_ok=True)
        print(f"{bcolors.FAIL}")
        coco_builder(local_db, image_db, coco_dataset, zoom)
        message_queue.append("[INFO] Data Builder finished")
        print(f"{bcolors.ENDC}")

        # filter out images with no annotations
        print(f"{bcolors.WARNING}")
        filter_coco_image(coco_dataset)
        message_queue.append("[INFO] Filtered out images with no annotations")
        print(f"{bcolors.ENDC}")

        # OSM-GAN dataset builder
        osm_gan_path = os.path.join(session_dir, config["osm_gan"])
        osm_gan_dataset = os.path.join(osm_gan_path, "test")
        os.makedirs(osm_gan_dataset, exist_ok=True)
        print(f"{bcolors.OKCYAN}")
        osm_gan_data_builder(coco_dataset, osm_gan_dataset)
        message_queue.append("[INFO] OSM-GAN dataset builder finished")
        print(f"{bcolors.ENDC}")

        # OSM-GAN Prediction
        env = config["prediction"]["conda_env"]
        name = config["prediction"]["model_name"]
        model = config["prediction"]["model_func"]
        direction = config["prediction"]["direction"]
        num_test = len(os.listdir(osm_gan_dataset))
        print(
            f"{bcolors.FAIL}python test.py --dataroot {osm_gan_dataset} --name {name} --model {model} --direction {direction}  --num_test {num_test}{bcolors.ENDC}"
        )
        os.chdir("./libs/pix2pix")
        abs_osm_gan_path = os.path.join("..", "..", osm_gan_path)
        subprocess.call(
            f"python test.py --dataroot {abs_osm_gan_path} --name {name} --model {model} --direction {direction}  --num_test {num_test}",
            shell=True,
        )
        message_queue.append("[INFO] OSM-GAN Prediction finished")
        os.chdir("../../")
        pix2pix_result_dir = f"./libs/pix2pix/results/{name}/test_latest/images"
        result_path = os.path.join(
            osm_gan_path, "results", name, "test_latest", "images"
        )
        shutil.move(pix2pix_result_dir, result_path)
        message_queue.append("[INFO] OSM-GAN Predictions moved to results folder")
        # Change Detection
        # TODO: save the extracted changes in geojson format
        reg_changes_save_path = os.path.join(
            session_dir, config["REG"]["changes_save_path"]
        )
        reg_save_path = os.path.join(reg_changes_save_path, config["REG"]["save_path"])
        reg_changes_save_path_base = os.path.join(reg_changes_save_path, "changes")
        rdp_save_path = os.path.join(reg_changes_save_path, config["prediction"]["rdp_save_path"])
        
        print(f"======>{reg_save_path}<======")
        message_queue.append("[INFO] Change Detection started")
        os.makedirs(reg_changes_save_path_base, exist_ok=True)
        os.makedirs(reg_save_path, exist_ok=True)
        os.makedirs(rdp_save_path, exist_ok=True)
        print(f"{bcolors.OKCYAN}")
        change_detection(
            result_path,
            coco_dataset,
            config,
            local_db,
            reg_changes_save_path_base,
            reg_save_path,
            rdp_save_path
        )
        message_queue.append("[INFO] Change Detection finished")
        print(f"{bcolors.ENDC}")

        # Poly-GAN Prediction
        reg_model = config["REG"]["model_name"]
        num_test = len(os.listdir(reg_save_path))
        print(
            f"{bcolors.FAIL}python test.py --dataroot {reg_changes_save_path} --name {reg_model} --model {model} --direction {direction}  --num_test {num_test}{bcolors.ENDC}"
        )
        os.chdir("./libs/pix2pix")
        abs_reg_changes_save_path = os.path.join("..", "..", reg_changes_save_path)
        print(f"{bcolors.OKBLUE}")
        message_queue.append("[INFO] Poly-GAN Prediction started")
        subprocess.call(
            f"python test.py --dataroot {abs_reg_changes_save_path} --name {reg_model} --model {model} --direction {direction}  --num_test {num_test}",
            shell=True,
        )
        print(f"{bcolors.ENDC}")
        os.chdir("../../")
        polygan_result_dir = f"./libs/pix2pix/results/{reg_model}/test_latest/images"
        result_path = os.path.join(
            reg_changes_save_path, "results", reg_model, "test_latest", "images"
        )
        shutil.move(polygan_result_dir, result_path)
        final_save_path = os.path.join(reg_changes_save_path, config["REG"]["results_path"])
        os.makedirs(final_save_path, exist_ok=True)
        # Apply PD
        print(f"{bcolors.WARNING}")
        applyPerpendicularDistance(result_path, final_save_path)
        print(f"{bcolors.ENDC}")
        message_queue.append("[INFO] Poly-GAN regularization finished")

        # merge collided polygons
        geojson_root = os.path.join(session_dir, config["MERGE"]["geojson_root"])
        save_dir = os.path.join(geojson_root, config["MERGE"]["save_dir"])
        os.makedirs(geojson_root, exist_ok=True)
        os.makedirs(save_dir, exist_ok=True)
        files = [os.path.join(final_save_path, f) for f in os.listdir(final_save_path)]
        collision_groups = createCollisionsGraph(files, geojson_root, session_id)
        print(f"{len(collision_groups)} collision groups found.")
        print(f"{bcolors.WARNING}")
        for i, group in enumerate(collision_groups):
            print(f"Group {i+1}:")
            # if length of group is one, copy the file into save destination
            if len(group) == 1:
                print(list(group)[0])
                print()
                shutil.copy(list(group)[0], os.path.join(save_dir, f"group_{i+1}.geojson"))
                continue
            else:
                for file in group:
                    print(file)
                print()
                PolyMerge(list(group), save_dir, f"group_{i+1}.geojson")
        print(f"{bcolors.ENDC}")
        message_queue.append("[INFO] Polygons merged")

        # send the geojson files to the frontend
        geojson_root = os.path.join(session_dir, config["MERGE"]["geojson_root"])
        save_dir = os.path.join(geojson_root, config["MERGE"]["save_dir"])
        files = [os.path.join(save_dir, f) for f in os.listdir(save_dir)]
        changesets = []
        geojsons = []
        # send the geojson files to the frontend
        for file in files:
            print(file)
            gdf = gpd.read_file(file)
            gdf = gdf.to_crs({'init': 'epsg:4326'})
            geojson = gdf.to_json()
            geojsons.append(geojson)

            changeset = buildChangeSet("building", gdf.geometry[0].exterior.coords, config)
            print(changeset)
            changesets.append(changeset)

        return render_template('map_QA.html', geojsons=geojsons, changesets=changesets)
    # return {"messages" : message_queue}

@app.route("/map")
def map():
    geojson_root = os.path.join(session_dir, config["MERGE"]["geojson_root"])
    save_dir = os.path.join(geojson_root, config["MERGE"]["save_dir"])
    files = [os.path.join(save_dir, f) for f in os.listdir(save_dir)]
    changesets = []
    geojsons = []
    # send the geojson files to the frontend
    for file in files:
        print(file)
        gdf = gpd.read_file(file)
        gdf = gdf.to_crs({'init': 'epsg:4326'})
        geojson = gdf.to_json()
        geojsons.append(geojson)
        print("=================================")
        print(type(geojson))
        print("=================================")
        changeset = buildChangeSet("building", gdf.geometry[0].exterior.coords, config)
        print(changeset)
        changesets.append(changeset)

    return render_template('map_QA.html', geojsons=geojsons, changesets=changesets)
    # Create the Leaflet map object
    # use folium Google map
    """
    m = folium.Map(location=[53.356225,-6.281595], zoom_start=17, control_scale=True)

    # Add Google Earth imagery tiles as the base map
    tiles = 'https://www.google.com/maps/vt/lyrs=s&x={x}&y={y}&z={z}'
    attr = 'Google'
    folium.raster_layers.TileLayer(tiles=tiles, attr=attr, name='Google Earth').add_to(m)

    # Add the Leaflet-geoman library to the map
    # folium.TileLayer('https://unpkg.com/@geoman-io/leaflet-geoman-free@2.10.1/dist/leaflet-geoman.min.js',
    #              name='Leaflet-Geoman', attr='Leaflet-Geoman').add_to(m)
    # folium.plugins.GeomanControl().add_to(m)

    # Create a FeatureGroup object to hold all the GeoJSON layers
    feature_group = folium.FeatureGroup(name="GeoJSON Layer")    

    # loop through each geojson file and add it to the map
    for file in files:
        with open(file) as f:
            gj = json.load(f)
        for feature in gj['features']:
            feature['properties'] = {}  # make the feature editable
        geojson_layer = folium.GeoJson(data=gj, name=file,  style_function=lambda x: {'color': webcolors.rgb_to_hex(random_color()), 'weight': 4, 'fillOpacity': 0.5})
        geojson_layer.add_to(m)


    # add edit control plugin for editing geojson features
    edit_control = Draw(export=True, position='topleft',  draw_options={'polyline': False, 'polygon': True, 'rectangle': True, 'circle': False, 'marker': False, 'circlemarker': False})
    edit_control.add_to(m)

    # add layer control to toggle geojson layers on and off
    folium.LayerControl().add_to(m)

    return m._repr_html_()
    """

# catch /save_edits POST request from the frontend
@app.route("/save_edits", methods=["POST"])
def save_edits():
    data = request.get_json()
    _id = data["id"]
    feature = data["feature"]
    # save the feature to the database
    return {"status": "success", "feature": feature, "id": _id}

@app.route("/show_cache")
def show_cache():
    # return cache.json
    return send_file("cache.json")



if __name__ == "__main__":
    # socketio.run(app, port=5000, debug=True)
    app.run()