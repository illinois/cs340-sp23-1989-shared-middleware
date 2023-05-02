from dotenv import load_dotenv
load_dotenv()

import requests
import time
from flask import Flask, jsonify, render_template, request
import asyncio
import aiohttp

mmg_servers = {}

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

    mmg_servers[name] = {
        "url": url,
        "author": author,
    }
    print(f"Added {name}: {url} by {author}")
    return "Success :)", 200

async def make_request(url, tilesAcross, renderedTileSize, image_data):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{url}?tilesAcross={tilesAcross}&renderedTileSize={renderedTileSize}',
            data={"image": image_data}
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
        image_data = input_file.read()

        threads = []
        for idx, (theme, server_info) in enumerate(mmg_servers.items(), 1):
            try:
                print(f"Generating {theme} mosiac ({idx}/{len(mmg_servers)})")
                mg_url = server_info["url"]
                thread = asyncio.create_task(make_request(mg_url, request.form["tilesAcross"], request.form["renderedTileSize"], image_data))
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
    