from dotenv import load_dotenv
load_dotenv()

import requests
import time
import base64
import os
import uuid
from flask import Flask, jsonify, render_template, request
import threading
from flask_socketio import SocketIO

mg_ports = {}
response = []

app = Flask(__name__)
socketio = SocketIO(app)

lock = threading.Lock()
def threadMMG(mg_url,base_img_name,tilesAcross,renderedTileSize):
    req = requests.post(f'{mg_url}?tilesAcross={tilesAcross}&renderedTileSize={renderedTileSize}',
                files={"image": open(base_img_name, "rb")}
            )
    global response
    with lock:
        response += req.json()

@app.route("/", methods=["GET"])
def GET_index():
    """Route for "/" (frontend)"""
    return render_template("index.html")


@app.route("/addMMG", methods=["PUT"])
def PUT_addMMG():
    """Add a mosaic microservice generator"""
    name = request.form["name"]
    url = request.form["url"]
    author = request.form["author"]

    mg_ports[name] = url
    print(f"Added {name}: {url} by {author}")
    return "Success :)", 200


@app.route("/makeMosaic", methods=["POST"])
def POST_makeMosaic():
    """Route to generate mosaic"""
    global response
    response = []
    try:
        start_time = time.time()
        print("Reading in base file")
        input_file = request.files["image"]
        filetype = input_file.filename.split(".")[-1]
        base_img_name = f"temp-{uuid.uuid4()}.{filetype}"
        input_file.save(base_img_name)
        tasks = []
        for idx, (theme, mg_url) in enumerate(mg_ports.items(), 1):
            print(f"Generating {theme} mosiac ({idx}/{len(mg_ports)})")
            t = threading.Thread(target=threadMMG,args=(mg_url,base_img_name,request.form["tilesAcross"],request.form["renderedTileSize"]))
            tasks.append(t)
            t.start()
        while not (len(response) == len(mg_ports)):
            time.sleep(1)
            socketio.emit("progress update",str(len(response)/len(mg_ports)))

        for t in tasks:
            t.join()
            
        os.system(f"rm {base_img_name}")
        print(
            f"Spent {time.time() - start_time} seconds to generate {len(mg_ports)} images"
        )
    
    except Exception as e:
        print(e)
        with open("static/favicon.png", "rb") as f:
            buffer = f.read()
            b64 = base64.b64encode(buffer)
            response.append({"image": "data:image/png;base64," + b64.decode("utf-8")})

    return jsonify(response)