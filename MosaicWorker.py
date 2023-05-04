import asyncio
import requests
import random
import base64

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
     

  async def awaitReducer(self, mosaic1, mosaic2):
    if len(self.reducersAvailable) == 0:
      raise Exception("No reducers are available on this server.")

    print(f'[MosaicWorker]: Sending reduce request for #{mosaic1["id"]} and #{mosaic2["id"]}')

    reducer = random.choice( self.reducersAvailable )
    url = reducer["url"]
    print(f'[MosaicWorker]:   url: {url}')

    req = requests.post(
      f'{url}?tilesAcross={self.tilesAcross}&renderedTileSize={self.renderedTileSize}&fileFormat={self.fileFormat}',
      files = {
        "baseImage": self.baseImage,
        "mosaic1": mosaic1["mosaicImage"],
        "mosaic2": mosaic2["mosaicImage"],
      }
    )

    mosaicImage = req.content
    self.processRenderedMosaic(
      mosaicImage,
      f'Reduction of #{mosaic1["id"]} and #{mosaic2["id"]}',
      mosaic1["tiles"] + mosaic2["tiles"]
    )

    self.reducerCompleted = self.reducerCompleted + 1
    reducer['count']+=1


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
      return

    mosaicImage = req.content
    self.processRenderedMosaic(mosaicImage, f"\"{name}\" by {author}", mmg["tiles"])

    self.mmgCompleted = self.mmgCompleted + 1
    mmg['count']+=1
    #socketio.emit("progress update", str(completed / len(mmg_servers)))


  async def createMosaic(self):
    if len(self.mmgsAvailable) == 0:
      raise Exception("No MMGs are available on this server.")

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
