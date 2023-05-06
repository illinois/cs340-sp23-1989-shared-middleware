import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests
import random
import base64
import concurrent

class MosaicWorker:
  def __init__(self, baseImage, tilesAcross, renderedTileSize, fileFormat, socketio, socketio_filter = ""):
    self.baseImage = baseImage
    self.tilesAcross = tilesAcross
    self.renderedTileSize = renderedTileSize
    self.fileFormat = fileFormat
    self.socketio = socketio
    self.socketio_filter = socketio_filter
    
    self.mmgsAvailable = []
    self.reducersAvailable = []
    self.reducerQueue = []

    self.mmgTasks = []
    self.reducerTasks = []

    self.mmgCompleted = 0
    self.reducerCompleted = 0
    self.mosaicNextID = 1
    self.expectedMosaics = -1   # Always (2*MG - 1) mosaics w/ reductions; start with -1 and always add 2.
    self.disableReduce = False

    self.threadPool = ThreadPoolExecutor(max_workers=8)

  def addMMG(self, mmg):
    self.mmgsAvailable.append(mmg)
    self.expectedMosaics += 2

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
    self.socketio.emit("mosaic" + self.socketio_filter, mosaicInfo)


    self.reducerQueue.append({
      "mosaicImage": mosaicImage,
      "id": self.mosaicNextID,
      "tiles": tiles,
    })
    self.socketio.emit("progress update" + self.socketio_filter, str(self.mosaicNextID / self.expectedMosaics))
    self.mosaicNextID = self.mosaicNextID + 1

    if len(self.reducerQueue) >= 2 and not self.disableReduce:
      mosaic1 = self.reducerQueue.pop()
      mosaic2 = self.reducerQueue.pop()

      #reducerTask = asyncio.create_task(self.awaitReducer(mosaic1, mosaic2))
      reducerTask = self.threadPool.submit(self.awaitReducer(mosaic1, mosaic2))
      self.reducerTasks.append(reducerTask)
     

  def sendRequest2(self, url, files):
    return requests.post(
      f'{url}?tilesAcross={self.tilesAcross}&renderedTileSize={self.renderedTileSize}&fileFormat={self.fileFormat}',
      files = files
    )


  async def sendRequest(self, url, files):
    # return await client.post(
    #   f"{url}?tilesAcross={self.tilesAcross}&renderedTileSize={self.renderedTileSize}&fileFormat={self.fileFormat}",
    #   files = files
    # )

    # return requests.post(
    #   f'{url}?tilesAcross={self.tilesAcross}&renderedTileSize={self.renderedTileSize}&fileFormat={self.fileFormat}',
    #   files = files
    # )

    return await asyncio.to_thread(self.sendRequest2, url, files)


  def awaitReducer(self, mosaic1, mosaic2):
    if len(self.reducersAvailable) == 0:
      raise Exception("No reducers are available on this server.")

    print(f'[MosaicWorker]: Sending reduce request for #{mosaic1["id"]} and #{mosaic2["id"]}')

    reducer = random.choice( self.reducersAvailable )
    url = reducer["url"]
    print(f'[MosaicWorker]:   url: {url}')


    error = None
    req = None
    try:
      req = self.sendRequest2(url, files = {"baseImage": self.baseImage, "mosaic1": mosaic1["mosaicImage"], "mosaic2": mosaic2["mosaicImage"]})
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
      reducerFuture = self.threadPool.submit(self.awaitReducer(mosaic1, mosaic2))
      self.reducerTasks.append(reducerFuture)
      return



    self.processRenderedMosaic(
      mosaicImage,
      f'Reduction of #{mosaic1["id"]} and #{mosaic2["id"]} by {reducer["author"]}',
      mosaic1["tiles"] + mosaic2["tiles"]
    )

    self.reducerCompleted = self.reducerCompleted + 1
    reducer['count'] += 1


  def awaitMMG(self, mmg):
    url = mmg["url"]
    name = mmg["name"]
    author = mmg["author"]
    print(f"[MosaicWorker]: Sending MMG request to \"{name}\" by {author} at {url}")

    try:
      req = self.sendRequest2(url, files={"image": self.baseImage})
    except Exception as e:
      mmg["error"] = f"ConnectionError: {e}"
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


  def createMosaic(self):
    if len(self.mmgsAvailable) == 0:
      raise Exception("No MMGs are available on this server.")

    random.shuffle(self.mmgsAvailable)

    for mmg in self.mmgsAvailable:
       mmgFuture = self.threadPool.submit(self.awaitMMG(mmg))
       self.mmgTasks.append(mmgFuture)

    concurrent.futures.wait(self.mmgTasks)
    concurrent.futures.wait(self.reducerTasks)

    self.threadPool.shutdown(wait=True, cancel_futures=False)

    # After all MMGs and reducers, there should be one mosaic that remains to be reduced that cannot
    # be reduced with anything else.  This is the final result:

    # if len(self.allRenderedMosaics) > 0:
    #   for d in self.allRenderedMosaics:
    #     d["image"] = "data:image/png;base64," + base64.b64encode(d["image"]).decode("utf-8")
    #   return self.allRenderedMosaics
    print(len(self.reducerQueue))
    if len(self.reducerQueue) == 1:
      mosaicImage_buffer = self.reducerQueue[0]["mosaicImage"]
      mosaicImage_b64 = base64.b64encode(mosaicImage_buffer).decode("utf-8")
      return [{"image": "data:image/png;base64," + mosaicImage_b64}]
  
    # Otherwise, we have some sort of an error:
    raise Exception("No mosaics were available after all threads completed all of the work.  (Did every MMG fail?)")

  def testMosaic(self):
    if len(self.mmgsAvailable) == 0:
      raise Exception("No MMGs are available for this author.")

    self.disableReduce = True
    for mmg in self.mmgsAvailable:
       mmgFuture = self.threadPool.submit(self.awaitMMG(mmg))
       self.mmgTasks.append(mmgFuture)

    concurrent.futures.wait(self.mmgTasks)
    return []

  def testReduction(self, mosaic1, mosaic2):
    if len(self.reducersAvailable) == 0:
      raise Exception("No reducers are available for this author.")
    
    m1 = { "id": "A", "mosaicImage": mosaic1, "tiles": -1 }
    m2 = { "id": "B", "mosaicImage": mosaic2, "tiles": -1 }

    reducerFuture = self.threadPool.submit(self.awaitReducer(m1, m2))
    self.reducerTasks.append(reducerFuture)

    concurrent.futures.wait(self.reducerTasks)
    self.threadPool.shutdown(wait=True, cancel_futures=False)

    return []