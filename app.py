from dotenv import load_dotenv

from ServersCollection import ServersCollection
load_dotenv()

from flask import Flask, jsonify, make_response, render_template, request
from flask_socketio import SocketIO
from MosaicWorker import MosaicWorker
import os 
from urllib.parse import quote_plus

app = Flask(__name__)
app.jinja_env.filters['quote_plus'] = lambda u: quote_plus(u)

socketio = SocketIO(app)

useDB = False
if os.getenv("ADMIN_PASSCODE"):
    useDB = True

servers = ServersCollection(useDB)

os.makedirs("mosaics", exist_ok=True)


from concurrent.futures import ThreadPoolExecutor
threadPool = ThreadPoolExecutor(max_workers=30)

@app.route("/", methods=["GET"])
def GET_index():
    """Route for "/" (frontend)"""

    disableInterface = False
    if os.getenv("ADMIN_PASSCODE"):
        disableInterface = True

        if "admin" in request.cookies and request.cookies.get("admin") == os.getenv("ADMIN_PASSCODE"):
            disableInterface = False

    return render_template("index.html", data={"disableInterface": disableInterface})


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
    result = servers.addMMG(
        name = request.form["name"],
        url = request.form["url"],
        author = request.form["author"],
        tiles = int(request.form["tileImageCount"]),
    )

    return jsonify(result["id"]), 200


@app.route("/registerReducer", methods=["PUT"])
def PUT_registerReducer():
    """Registers a reducer"""

    # Check for required fields:
    for requiredField in ["url", "author"]:
        if requiredField not in request.form:
            error = f"Required field {requiredField} is not present in /registerReducer request."
            print(f"❌ REJECTED /registerReducer: {error}")
            return jsonify({"error": error})

    result = servers.addReducer(
        url = request.form["url"],
        author = request.form["author"],
    )

    return jsonify(result["id"]), 200


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
            servers = servers,
            socketio = socketio,
            threadPool = threadPool,
        )


        # MMGs and Filtering
        filterQuery = request.form["filter"]
        if filterQuery == "":
            filterQuery = False

        for id in servers.mmgs:
            mmg = servers.mmgs[id]
            if filterQuery and filterQuery not in mmg["name"]:
                continue

            if "disabled" in mmg and mmg["disabled"]:
                continue

            worker.addMMG( mmg )
        

        # Reducers and Verification
        verifiedOnly = False
        if "verified" in request.form:
            verifiedOnly = True

        for id in servers.reducers:
            reducer = servers.reducers[id]
            if verifiedOnly and reducer["verification"] != "GOOD":
                continue

            if "disabled" in reducer and reducer["disabled"]:
                continue

            worker.addReducer( reducer )

        result = worker.createMosaic()
        return jsonify(result)

    except KeyError as e:
        print(e)
        return jsonify({"error": "Please upload an image file."}), 400
    
    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({"error": str(e)}), 400


@app.route("/serverList", methods=["GET"])
def GET_serverList():
    """Route to get connected servers"""
    servers_by_author = {}
    for key in servers.mmgs:
        mmg = servers.mmgs[key]
        author = mmg["author"]
        if author not in servers_by_author:
            servers_by_author[author] = []
        servers_by_author[author].append(mmg)
      
    for key in servers.reducers:
        reducer = servers.reducers[key]
        author = reducer["author"]
        if author not in servers_by_author:
            servers_by_author[author] = []
        servers_by_author[author].append(reducer)

    return render_template("servers.html", data=servers_by_author)


def isAdmin():
    if os.getenv("ADMIN_PASSCODE") and "admin" in request.cookies and request.cookies.get("admin") == os.getenv("ADMIN_PASSCODE"):
        return True
    else:
        return False

@app.route("/singleAuthor", methods=["GET"])
def GET_singleAuthor():
    if not isAdmin():
        return render_template("disabled.html")

    author = request.args.get("author")
    return render_template("singleAuthor.html", data={"author": author, "isAdmin": isAdmin()})


def verify(how):
    if not isAdmin():
        return jsonify({"error": "This server is currently in admin-only mode. You are unable to add an image."}), 400

    author = request.args.get("author")
    for key in servers.reducers:
        reducer = servers.reducers[key]
        if author == reducer["author"]:
            servers.updateValue(reducer, "verification", how)
            return jsonify({"verification": how})
            
    return jsonify({"error": "author not found"})

@app.route("/verify_GOOD", methods=["GET"])
def GET_verify_GOOD():
    return verify("GOOD")

@app.route("/verify_BROKEN", methods=["GET"])
def GET_verify_BROKEN():
    return verify("BROKEN")

@app.route("/toggleLate", methods=["GET"])
def GET_toggleLate():
    if not isAdmin(): return jsonify({"error": "Requires Admin"})
    return jsonify({"result": servers.toggleAfterDeadline()})

@app.route("/clearErrors", methods=["GET"])
def GET_clearErrors():
    if not isAdmin(): return jsonify({"error": "Requires Admin"})
    return jsonify({"result": servers.clearErrors()})



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

imgC = None
with open("testFiles/C.png", "rb") as f:
    imgC = f.read()

imgD = None
with open("testFiles/D.png", "rb") as f:
    imgD = f.read()


@app.route("/testMosaic", methods=["GET"])
async def GET_testMosaic():
    if not isAdmin():
        return jsonify({"error": "Requires admin access."}), 400

    author = request.args.get("author")

    worker = MosaicWorker(
        baseImage = rainbowTest,
        tilesAcross = 50,
        renderedTileSize = 10,
        fileFormat = "PNG",
        socketio = socketio,
        servers = servers,
        threadPool = threadPool,
        socketio_filter = f" {author}",
    )

    for id in servers.mmgs:
        mmg = servers.mmgs[id]
        if "disabled" in mmg and mmg["disabled"]:
            continue

        if mmg["author"] == author:
            worker.addMMG( mmg )    

    for id in servers.reducers:
        reducer = servers.reducers[id]
        if "disabled" in reducer and reducer["disabled"]:
            continue

        if reducer["author"] == author:
            worker.addReducer( reducer )        

    try:
        worker.testMosaic()
        worker.testReduction(imgA, imgB, imgC, imgD)

        return jsonify([])
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400

