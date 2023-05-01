from dotenv import load_dotenv
load_dotenv()

import requests
import time
import base64
import os
import uuid
from flask import Flask, jsonify, render_template, request
import asyncio
import aiohttp

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

async def make_request(url, tilesAcross, renderedTileSize, base_img_name):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{url}?tilesAcross={tilesAcross}&renderedTileSize={renderedTileSize}',
            data={"image": open(base_img_name, "rb")}
        ) as response:
            return await response.json()

@app.route("/makeMosaic", methods=["POST"])
async def POST_makeMosaic():
    """Route to generate mosaic"""
    response = []
    try:
        start_time = time.time()
        print("Reading in base file")
        input_file = request.files["image"]
        filetype = input_file.filename.split(".")[-1]
        base_img_name = f"temp-{uuid.uuid4()}.{filetype}"
        input_file.save(base_img_name)


        threads = []
        for idx, (theme, mg_url) in enumerate(mg_ports.items(), 1):
            try:
                print(f"Generating {theme} mosiac ({idx}/{len(mg_ports)})")
                thread = asyncio.create_task(make_request(mg_url, request.form["tilesAcross"], request.form["renderedTileSize"], base_img_name))
                threads.append(thread)
            except:
                with open("static/favicon.png", "rb") as f:
                    buffer = f.read()
                    b64 = base64.b64encode(buffer)
                    response.append({"image": "data:image/png;base64," + b64.decode("utf-8")})

        
        images = await asyncio.gather(*threads)

        for img in images:
            response+=img

        os.system(f"rm {base_img_name}")
        print(
            f"Spent {time.time() - start_time} seconds to generate {len(mg_ports)} images"
        )
    except:
        with open("static/favicon.png", "rb") as f:
            buffer = f.read()
            b64 = base64.b64encode(buffer)
            response.append({"image": "data:image/png;base64," + b64.decode("utf-8")})
            
            os.system(f"rm {base_img_name}")

    return jsonify(response)
