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

"""Default Values if not passing in valid values for tilesAcross and renderedTileSize"""
TILES_ACORSS = 200
RENDERED_TILE_SIZE = 16

"""Default Max Values for tilesAcross and renderedTileSize, not sure what would be a good number, perhaps something related to memories?"""
MAX_TILES_ACORSS = 1000
MAX_RENDERED_TILE_SIZE = 64
MAX_PIXEL = 64000


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
        filetype = input_file.filename.split(".")[-1]
        base_img_name = f"temp-{uuid.uuid4()}.{filetype}"
        input_file.save(base_img_name)

        for idx, (theme, mg_url) in enumerate(mg_ports.items(), 1):
            print(f"Generating {theme} mosaic ({idx}/{len(mg_ports)})")
            tilesAcross = request.form["tilesAcross"]
            renderedTileSize = request.form["renderedTileSize"]
            """
            Checking the input for tilesAcross and renderedTileSize, having conditions below will set the value to default:
            1) Input is not exist
            2) Negative Input
            3) tilesAcross or renderedTileSize is too huge
            4) Non-integer input
            """
            if tilesAcross == '' or tilesAcross == None or float(tilesAcross) <= 0 or float(tilesAcross) > MAX_TILES_ACORSS or float(tilesAcross) != int(float(tilesAcross)):
                tilesAcross = TILES_ACORSS
            if renderedTileSize == '' or renderedTileSize == None or float(renderedTileSize) <= 0 or float(renderedTileSize) > MAX_RENDERED_TILE_SIZE or float(renderedTileSize) != int(float(renderedTileSize)):
                renderedTileSize = RENDERED_TILE_SIZE
            if tilesAcross * renderedTileSize > MAX_PIXEL:
                tilesAcross = TILES_ACORSS
                renderedTileSize = RENDERED_TILE_SIZE
            req = requests.post(
                f'{mg_url}?tilesAcross={tilesAcross}&renderedTileSize={renderedTileSize}',
                files={"image": open(base_img_name, "rb")}
            )
            response += req.json()

        os.system(f"rm {base_img_name}")
        print(
            f"Spent {time.time() - start_time} seconds to generate {len(mg_ports)} images"
        )
    except:
        with open("static/favicon.png", "rb") as f:
            buffer = f.read()
            b64 = base64.b64encode(buffer)
            response.append({"image": "data:image/png;base64," + b64.decode("utf-8")})
    
    finally:
        """I do not want to save the input files, remove the base image file after use"""
        if os.path.exists(base_img_name):
            os.remove(base_img_name)

    return jsonify(response)


if __name__ == "__main__":
    app.run(port=34000)