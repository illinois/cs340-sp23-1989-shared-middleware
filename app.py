from dotenv import load_dotenv
load_dotenv()

# import eventlet
# eventlet.monkey_patch()

from flask import Flask, jsonify, render_template, request
import secrets
from flask_socketio import SocketIO
from MosaicWorker import MosaicWorker

mmg_servers = {}
reducers = {}

app = Flask(__name__)
if __name__ == '__main__':
    socketio = SocketIO(app, async_mode="eventlet")
else:
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
    count = 0

    # Check for existing MMG with same URL:
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

    # Check for existing MMG with same URL:
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
            if "disabled" not in mmg_servers[id]:
                worker.addMMG( mmg_servers[id] )
        
        for id in reducers:
            if "disabled" not in reducers[id]:
                worker.addReducer( reducers[id] )

        result = await worker.createMosaic()
        return jsonify(result)

    except KeyError as e:
        print(e)
        return jsonify({"error": "Please upload an image file."}), 400
    
    except Exception as e:
        print(e)
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



# if __name__ == '__main__':
#     socketio.run(app, "0.0.0.0", 5000, debug=True)
