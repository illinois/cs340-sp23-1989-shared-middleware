from dotenv import load_dotenv
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
    name = request.form["name"]
    url = request.form["url"]
    author = request.form["author"]
    id = secrets.token_hex(20)

    mmg_servers[id] = {
        "id": id,
        "name": name,
        "url": url,
        "author": author,
    }
    print(f"Added {name}: {url} by {author}")
    return "Success :)", 200


@app.route("/registerReducer", methods=["PUT"])
def PUT_registerReducer():
    """Registers a reducer"""
    url = request.form["url"]
    author = request.form["author"]
    id = secrets.token_hex(20)

    reducers[id] = {
        "id": id,
        "url": url,
        "author": author,
    }
    print(f"Added reducer: {url} by {author}")
    return "Success :)", 200


completed = 0

async def make_request(url, tilesAcross, renderedTileSize, image_data):
    global completed
    req = requests.post(
        f'{url}?tilesAcross={tilesAcross}&renderedTileSize={renderedTileSize}',
        files={"image": image_data}
    )

    completed = completed + 1
    socketio.emit("progress update", str(completed / len(mmg_servers)))

    return req.json()

@app.route("/makeMosaic", methods=["POST"])
async def POST_makeMosaic():
    """Route to generate mosaic"""
    global completed
    completed = 0

    response = []
    try:
        start_time = time.time()
        print("Reading in base file")
        input_file = request.files["image"]

        image_data = input_file.read()

        threads = []
        for idx, (id, server_info) in enumerate(mmg_servers.items(), 1):
            try:
                url = server_info["url"]
                name = server_info["name"]

                print(f"Generating {name} mosaic ({idx}/{len(mmg_servers)})")
                thread = asyncio.create_task(make_request(url, request.form["tilesAcross"], request.form["renderedTileSize"], image_data))
                threads.append(thread)
            except Exception as e:
                print(e)

        images = await asyncio.gather(*threads)
        for img in images:
            response += img

        print(
            f"Spent {time.time() - start_time} seconds to generate {len(mmg_servers)} images"
        )

    except KeyError as e:
        print(e)
        response.append({"error": "Please upload an image file."})
    except requests.exceptions.RequestException as e:
        print(e)
        response.append({"error": "Failed to connect to remote server."})
    except requests.exceptions.ConnectionError as e:
        print(e)
        mg_ports.pop(theme)

    
    return jsonify(response)

@app.route("/serverList", methods=["GET"])
def GET_serverList():
  """Route to get connected servers"""
  return render_template("servers.html", data=mmg_servers)
    
