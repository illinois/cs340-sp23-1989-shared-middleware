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
from flask_sqlalchemy import SQLAlchemy

mmg_servers = {}
reducers = {}

app = Flask(__name__)
socketio = SocketIO(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///middleware.db'
db = SQLAlchemy(app)

class MMG(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    url = db.Column(db.String(120), nullable=False)
    author = db.Column(db.String(80), nullable=False)
    tiles = db.Column(db.Integer, nullable=False)
    count = db.Column(db.Integer, nullable=False)

class Reducer(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    url = db.Column(db.String(120), nullable=False)
    author = db.Column(db.String(80), nullable=False)
    count = db.Column(db.Integer, nullable=False)

with app.app_context():
    db.create_all()

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
    count = 0

    # Check for existing MMG with same URL in DB:
    existing_mmg = MMG.query.filter_by(url=url).first()
    if existing_mmg:
        id = existing_mmg.id
        count = existing_mmg.count
    # Check for existing MMG with same URL in memory:
    for existingId in mmg_servers:
        if mmg_servers[existingId]["url"] == url:
            id = existingId
            count = mmg_servers[existingId]["count"]
            break

    mmg_servers[id] = {
        "id": id,
        "name": name,
        "url": url,
        "author": author,
        "tiles": tileImageCount,
        "count": count
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
    count = 0

    # Check for existing Reducer with same URL in DB:
    existing_reducer = Reducer.query.filter_by(url=url).first()
    if existing_reducer:
        id = existing_reducer.id
        count = existing_reducer.count
    # Check for existing Reducer with same URL in memory:
    for existingId in reducers:
        if reducers[existingId]["url"] == url:
            id = existingId
            count = reducers[existingId]["count"]
            break

    reducers[id] = {
        "id": id,
        "url": url,
        "author": author,
        "type": "reducer",
        "count": count
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
            tilesAcross = int(request.form["tilesAcross"]),
            renderedTileSize = int(request.form["renderedTileSize"]),
            fileFormat = request.form["fileFormat"],
            socketio = socketio,
        )
        for id in mmg_servers:
            worker.addMMG( mmg_servers[id] )
        
        for id in reducers:
            worker.addReducer( reducers[id] )

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
    servers_by_author = {}
    for key in mmg_servers:
        mmg = mmg_servers[key]
        author = mmg["author"]
        if author not in servers_by_author:
            servers_by_author[author] = []
        servers_by_author[author].append(mmg)
      
    for key in reducers:
        reducer = reducers[key]
        author = reducer["author"]
        if author not in servers_by_author:
            servers_by_author[author] = []
        servers_by_author[author].append(reducer)

    return render_template("servers.html", data=servers_by_author)

@app.route("/uploadData", methods=["POST"])
def upload_data():
    """Route to upload data to the database"""
    data_type = request.form.get("type")
    name = request.form.get("name", default=None)
    url = request.form.get("url")
    author = request.form.get("author")
    count = request.form.get("count", type=int)
    tileImageCount = request.form.get("tileImageCount", default=None, type=int)

    if data_type == "mmg":
        # Check for existing MMG with same URL in database
        existing_mmg = MMG.query.filter_by(url=url).first()
        if existing_mmg:
            # If mmg aready in db and the count is the same, then we don't need to update the database
            if existing_mmg.count == count: return jsonify({"message": "Data already uploaded"}), 200
            else: existing_mmg.count = count
        else:
            # Upload new mmg to database
            mmg = MMG(id=secrets.token_hex(20), name=name, url=url, author=author, tiles=tileImageCount, count=count)
            db.session.add(mmg)

    elif data_type == "reducer":
        # Check for existing Reducer with same URL in database
        existing_reducer = Reducer.query.filter_by(url=url).first()
        if existing_reducer:
            # If reducer aready in db and the count is the same, then we don't need to update the database
            if existing_reducer.count == count: return jsonify({"message": "Data already uploaded"}), 200
            else: existing_reducer.count = count
        else:
            # Upload new reducer to database
            reducer = Reducer(id=secrets.token_hex(20), url=url, author=author, count=count)
            db.session.add(reducer)

    else:
        # Invalid data type (should never happen)
        return jsonify({"error": "Invalid data type"}), 400
    
    # Commit changes to database
    db.session.commit()
    return jsonify({"message": "Data successfully uploaded"}), 200