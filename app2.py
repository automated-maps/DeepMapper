# from flask import Flask, render_template
# from flask_socketio import SocketIO, emit, disconnect

# from time import sleep

# async_mode = None

# app = Flask(__name__)

# socket_ = SocketIO(app, async_mode=async_mode)

# @app.route("/")
# def index():
#     return render_template("index_2.html", sync_mode=socket_.async_mode)

# @socket_.on("do_task", namespace="/test")
# def run_lengthy_task(data):
#     try:
#         duration = int(data["duration"])
#         sleep(duration)
#         emit("task_done", {"data": "long task of {} seconds complete".format(duration)})
#         disconnect()
#     except Exception as ex:
#         print(ex)


# if __name__ == "__main__":
#     socket_.run(app, port=5555, debug=True)


import os, sys
import glob
import time
import json
import shutil
from crawlers.utils import load_config, build_query, bcolors, filter_coco_image
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import eventlet

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, async_mode='eventlet')
session_id = 1111

@app.route("/")
def index():
    return render_template("index_2.html")


def send_notification(message):
    emit("notification", {"message": message}, namespace="/notifications")

@socketio.on("connect", namespace="/notifications")
def test_connect():
    print("Client connected")

@socketio.on("disconnect", namespace="/notifications")
def test_disconnect():
    print("Client disconnected")

@app.route("/process_polygon", methods=["POST"])
def process_polygon(session_id=session_id):

    # TODO: add a progress bar

    # Obtain the polygon coordinates from the form data
    polygon_coords = request.form.get("boxbounds")
    polygon_coords = polygon_coords.split(",")
    time.sleep(2)
    print(f"{bcolors.OKBLUE}[INFO] Polygon coordinates: {polygon_coords}{bcolors.ENDC}")
    send_notification(f"Polygon coordinates: {polygon_coords}")
    return jsonify(success=True)

if __name__ == '__main__':
    # Use eventlet to run the Flask app
    eventlet.wsgi.server(eventlet.listen(('127.0.0.1', 5000)), app, debug=True)
