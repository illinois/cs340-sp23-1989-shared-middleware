import base64
from dotenv import load_dotenv

from MosaicWorker import MosaicWorker
load_dotenv()

import requests
import time
from flask import Flask, jsonify, render_template, request
import asyncio
import secrets
from flask_socketio import SocketIO

mmg_servers = {}
reducers = {}

app = Flask(__name__)
socketio = SocketIO(app)


@app.route("/", methods=["GET"])
def GET_index():
    """Route for "/" (frontend)"""
    return render_template("index.html")


@app.route("/addMMG", methods=["PUT"])
def PUT_addMMG():
    """Add a mosaic microservice generator"""

    # Check for required fields:
    for requiredField in ["name", "url", "author", "tileImageCount"]:
        if requiredField not in request.form:
            error = f"Required field {requiredField} is not present in /addMMG request."
            print(f"❌ REJECTED /addMMG: {error}")
            return jsonify({"error": error})

    # Add the MMG:
    name = request.form["name"]
    url = request.form["url"]
    author = request.form["author"]
    tileImageCount = int(request.form["tileImageCount"])
    id = secrets.token_hex(20)

    mmg_servers[id] = {
        "id": id,
        "name": name,
        "url": url,
        "author": author,
        "errorStatus": None,
        "tiles": tileImageCount,
        "count": 0
    }
    print(f"✔️ Added MMG {name}: {url} by {author}")
    return "Success :)", 200


@app.route("/registerReducer", methods=["PUT"])
def PUT_registerReducer():
    """Registers a reducer"""

    # Check for required fields:
    for requiredField in ["url", "author"]:
        if requiredField not in request.form:
            error = f"Required field {requiredField} is not present in /registerReducer request."
            print(f"❌ REJECTED /registerReducer: {error}")
            return jsonify({"error": error})


    url = request.form["url"]
    author = request.form["author"]
    id = secrets.token_hex(20)

    reducers[id] = {
        "id": id,
        "url": url,
        "author": author,
        "count":0
    }
    print(f"✔️ Added reducer: {url} by {author}")
    return "Success :)", 200


@app.route("/makeMosaic", methods=["POST"])
async def POST_makeMosaic():
    """Route to generate mosaic"""
    global completed
    completed = 0

    try:
        input_file = request.files["image"]
        baseImage = input_file.read()

        worker = MosaicWorker(
            baseImage = baseImage,
            tilesAcross = request.form["tilesAcross"],
            renderedTileSize = request.form["renderedTileSize"],
            fileFormat = request.form["fileFormat"],
            socketio = socketio,
        )
        for id in mmg_servers:
            worker.addMMG( mmg_servers[id] )
            mmg_servers[id]['count'] +=1
        
        for id in reducers:
            worker.addReducer( reducers[id] )
            reducers[id]['count'] +=1

        result = await worker.createMosaic()
        return jsonify(result)

    except KeyError as e:
        print(e)
        return jsonify({"error": "Please upload an image file."}), 400
    
    except Exception as e:
        import traceback
        traceback.print_exception(e)
        return jsonify({"error": str(e)}), 400


@app.route("/serverList", methods=["GET"])
def GET_serverList():
  """Route to get connected servers"""
  return render_template("servers.html", data=mmg_servers)
    
@app.route("/reducerList", methods=["GET"])
def GET_reducerList():
  """Route to get connected servers"""
  return render_template("reducers.html", data=reducers)