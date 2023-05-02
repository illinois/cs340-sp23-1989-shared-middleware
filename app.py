from dotenv import load_dotenv
load_dotenv()

import requests
import time
import base64
import os
import uuid
from flask import Flask, jsonify, render_template, request

mg_ports = {}

app = Flask(__name__)

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
    response = []
    try:
        start_time = time.time()
        print("Reading in base file")
        input_file = request.files["image"]
        image_data = input_file.read()

        for idx, (theme, mg_url) in enumerate(mg_ports.items(), 1):
            print(f"Generating {theme} mosiac ({idx}/{len(mg_ports)})")
            req = requests.post(
                f'{mg_url}?tilesAcross={request.form["tilesAcross"]}&renderedTileSize={request.form["renderedTileSize"]}',
                files={"image": image_data}
            )
            response += req.json()

        print(
            f"Spent {time.time() - start_time} seconds to generate {len(mg_ports)} images"
        )
    except:
        with open("static/favicon.png", "rb") as f:
            buffer = f.read()
            b64 = base64.b64encode(buffer)
            response.append({"image": "data:image/png;base64," + b64.decode("utf-8")})

    return jsonify(response)
