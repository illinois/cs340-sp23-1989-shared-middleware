from dotenv import load_dotenv
load_dotenv()

# import eventlet
# eventlet.monkey_patch()

from flask import Flask, jsonify, make_response, render_template, request
import secrets
from flask_socketio import SocketIO
from MosaicWorker import MosaicWorker
import os 
from urllib.parse import quote_plus

mmg_servers = {}
reducers = {}

app = Flask(__name__)
app.jinja_env.filters['quote_plus'] = lambda u: quote_plus(u)

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

    if os.getenv("ADMIN_PASSCODE") and ("admin" not in request.cookies or request.cookies.get("admin") != os.getenv("ADMIN_PASSCODE")):
        return jsonify({"error": "This server is currently in admin-only mode. You are unable to add an image."}), 400

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

        result = worker.createMosaic()
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


@app.route("/singleAuthor", methods=["GET"])
def GET_singleAuthor():
    author = request.args.get("author")
    return render_template("singleAuthor.html", data={"author": author})

@app.route("/admin", methods=["GET"])
def GET_admin():
    return render_template("admin.html")

@app.route("/adminEnable", methods=["POST"])
def POST_adminEnable():
    cookie = request.form["cookie"]
    resp = make_response(render_template("admin.html"))
    resp.set_cookie("admin", cookie)
    return resp


rainbowTest = None
with open("testFiles/rainbow.png", "rb") as f:
    rainbowTest = f.read()

imgA = None
with open("testFiles/A.png", "rb") as f:
    imgA = f.read()

imgB = None
with open("testFiles/B.png", "rb") as f:
    imgB = f.read()


@app.route("/testMosaic", methods=["GET"])
async def GET_testMosaic():
    author = request.args.get("author")

    worker = MosaicWorker(
        baseImage = rainbowTest,
        tilesAcross = 50,
        renderedTileSize = 10,
        fileFormat = "PNG",
        socketio = socketio,
        socketio_filter = f" {author}",
    )

    for id in mmg_servers:
        mmg = mmg_servers[id]
        if mmg["author"] == author:
            worker.addMMG( mmg )    

    for id in reducers:
        reducer = reducers[id]
        if reducer["author"] == author:
            worker.addReducer( reducer )        

    try:
        worker.testMosaic()
        worker.testReduction(imgA, imgB)

        return jsonify([])
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    port = 5000
    if os.getenv("FLASK_RUN_PORT"):
        port = int(os.getenv("FLASK_RUN_PORT"))
    socketio.run(app, "0.0.0.0", port, debug=False)
