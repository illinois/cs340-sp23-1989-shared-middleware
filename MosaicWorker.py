import asyncio
import requests
import random
import base64
# import httpx

# limits = httpx.Limits(max_keepalive_connections=1000, max_connections=None, keepalive_expiry=30)
# client = httpx.AsyncClient(limits=limits, timeout=15)

class MosaicWorker:
  def __init__(self, baseImage, tilesAcross, renderedTileSize, fileFormat, socketio):
    self.baseImage = baseImage
    self.tilesAcross = tilesAcross
    self.renderedTileSize = renderedTileSize
    self.fileFormat = fileFormat
    self.socketio = socketio

    self.mmgsAvailable = []
    self.reducersAvailable = []
    self.reducerQueue = []

    self.mmgTasks = []
    self.reducerTasks = []

    self.mmgCompleted = 0
    self.reducerCompleted = 0
    self.mosaicNextID = 1

  def addMMG(self, mmg):
    self.mmgsAvailable.append(mmg)

  def addReducer(self, reducer):
    self.reducersAvailable.append(reducer)

  def getImageSize(self, imageBuffer):
    import struct
    import io
    from PIL import Image

    ## Check if PNG, just read from IHDR:
    if imageBuffer[0] == 137 and imageBuffer[1] == 80:
      width, height = struct.unpack('>ii', imageBuffer[16:24])

    ## Otherwise, use PIL:
    else:
      img = Image.open(io.BytesIO(imageBuffer))
      width = img.width 
      height = img.height

    return width, height


  def validateMosaicImageSize(self, server, baseImage, mosaicImage):
    try:
      baseWidth, baseHeight = self.getImageSize(baseImage)
      mosaicWidth, mosaicHeight = self.getImageSize(mosaicImage)
    except Exception as e:
      server["error"] = f"Image Error: {e}"
      return False

    d = baseWidth / self.tilesAcross
    verticalTiles = int(baseHeight / d)
 
    requiredWidth = int(self.tilesAcross * self.renderedTileSize)
    requiredHeight = int(verticalTiles * self.renderedTileSize)

    if mosaicWidth != requiredWidth or mosaicHeight != requiredHeight:
      server["error"] = f"Invalid mosaic image size: required ({requiredWidth} x {requiredHeight}), but mosaic was ({mosaicWidth}, {mosaicHeight})"
      return False
    
    return True


  def processRenderedMosaic(self, mosaicImage, description, tiles):
    """Stores a rendered mosaic, queueing up reduction or further reduction if possible."""
    print(f"[MosaicWorker]: --> Storing mosaic result as #{self.mosaicNextID}")
    print(f"[MosaicWorker]:     Bytes: {len(mosaicImage)}")

    mosaicInfo = {
      "image": mosaicImage,
      "id": self.mosaicNextID,
      "description": description,
      "tiles": tiles,
    }
    self.socketio.emit("mosaic", mosaicInfo)


    self.reducerQueue.append({
      "mosaicImage": mosaicImage,
      "id": self.mosaicNextID,
      "tiles": tiles,
    })
    self.socketio.emit("progress update", str(self.mosaicNextID / self.expectedMosaics))
    self.mosaicNextID = self.mosaicNextID + 1

    if len(self.reducerQueue) >= 2:
      mosaic1 = self.reducerQueue.pop()
      mosaic2 = self.reducerQueue.pop()

      reducerTask = asyncio.create_task(self.awaitReducer(mosaic1, mosaic2))
      self.reducerTasks.append(reducerTask)
     

  async def sendRequest(self, url, files):
    # return await client.post(
    #   f"{url}?tilesAcross={self.tilesAcross}&renderedTileSize={self.renderedTileSize}&fileFormat={self.fileFormat}",
    #   files = files
    # )

    return requests.post(
      f'{url}?tilesAcross={self.tilesAcross}&renderedTileSize={self.renderedTileSize}&fileFormat={self.fileFormat}',
      files = files
    )

  async def awaitReducer(self, mosaic1, mosaic2):
    if len(self.reducersAvailable) == 0:
      raise Exception("No reducers are available on this server.")

    print(f'[MosaicWorker]: Sending reduce request for #{mosaic1["id"]} and #{mosaic2["id"]}')

    reducer = random.choice( self.reducersAvailable )
    url = reducer["url"]
    print(f'[MosaicWorker]:   url: {url}')


    error = None
    req = None
    try:
      req = await self.sendRequest(url, files = {"baseImage": self.baseImage, "mosaic1": mosaic1["mosaicImage"], "mosaic2": mosaic2["mosaicImage"]})
    except Exception as e:
      reducer["disabled"] = True
      error = f"ConnectionError: {e}"
    
    if req:
      if req.status_code != 200:
        error = f"HTTP Status {req.status_code}"

      if req.status_code >= 500:
        reducer["disabled"] = True

      mosaicImage = req.content
      if not self.validateMosaicImageSize(reducer, self.baseImage, mosaicImage):
        reducer["disabled"] = True
        error = reducer["error"]

    if error:
      reducer["error"] = error
      # Remove bad reducer and retry:
      self.reducersAvailable.remove(reducer)
      await self.awaitReducer(mosaic1, mosaic2)
      return



    self.processRenderedMosaic(
      mosaicImage,
      f'Reduction of #{mosaic1["id"]} and #{mosaic2["id"]} by {reducer["author"]}',
      mosaic1["tiles"] + mosaic2["tiles"]
    )

    self.reducerCompleted = self.reducerCompleted + 1
    reducer['count'] += 1


  async def awaitMMG(self, mmg):
    url = mmg["url"]
    name = mmg["name"]
    author = mmg["author"]
    print(f"[MosaicWorker]: Sending MMG request to \"{name}\" by {author} at {url}")

    try:
      req = requests.post(
        f"{url}?tilesAcross={self.tilesAcross}&renderedTileSize={self.renderedTileSize}&fileFormat={self.fileFormat}",
        files={"image": self.baseImage}
      )
    except requests.exceptions.ConnectionError as e:
      mmg["error"] = "ConnectionError"
      mmg["disabled"] = True
      self.expectedMosaics -= 2
      return

    if req.status_code >= 500:
      mmg["disabled"] = True

    if req.status_code != 200:
      mmg["error"] = f"HTTP Status {req.status_code}"
      self.expectedMosaics -= 2
      return
    

    mosaicImage = req.content
    if not self.validateMosaicImageSize(mmg, self.baseImage, mosaicImage):
      self.expectedMosaics -= 2
      return

    self.processRenderedMosaic(mosaicImage, f"\"{name}\" by {author}", mmg["tiles"])
    self.mmgCompleted = self.mmgCompleted + 1
    mmg['count'] += 1


  async def createMosaic(self):
    if len(self.mmgsAvailable) == 0:
      raise Exception("No MMGs are available on this server.")

    random.shuffle(self.mmgsAvailable)
    self.expectedMosaics = (len(self.mmgsAvailable) * 2) - 1

    for mmg in self.mmgsAvailable:
       mmgTask = asyncio.create_task(self.awaitMMG(mmg))
       self.mmgTasks.append(mmgTask)

    await asyncio.gather(*self.mmgTasks)
    await asyncio.gather(*self.reducerTasks)

    # After all MMGs and reducers, there should be one mosaic that remains to be reduced that cannot
    # be reduced with anything else.  This is the final result:

    # if len(self.allRenderedMosaics) > 0:
    #   for d in self.allRenderedMosaics:
    #     d["image"] = "data:image/png;base64," + base64.b64encode(d["image"]).decode("utf-8")
    #   return self.allRenderedMosaics
    
    if len(self.reducerQueue) == 1:
      mosaicImage_buffer = self.reducerQueue[0]["mosaicImage"]
      mosaicImage_b64 = base64.b64encode(mosaicImage_buffer).decode("utf-8")
      return [{"image": "data:image/png;base64," + mosaicImage_b64}]

    
    # Otherwise, we have some sort of an error:
    raise Exception("No mosaics were available after all threads completed all of the work.  (Did every MMG fail?)")
