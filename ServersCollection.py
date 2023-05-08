

import secrets
import pymongo
from datetime import datetime

class ServersCollection:
  def __init__(self, usingMongo):
    self.isAfterDeadline = False
    self.usingMongo = usingMongo
    self.mmgs = {}
    self.reducers = {}

    if self.usingMongo:
      self.mongodb = pymongo.MongoClient()
      self.collection_mmgs = self.mongodb["1989"]["mmgs"]
      self.collection_reducers = self.mongodb["1989"]["reducers"]

      for mmg in self.collection_mmgs.find({}):
        self.mmgs[mmg["id"]] = mmg

      for reducer in self.collection_reducers.find({}):
        self.reducers[reducer["id"]] = reducer

  def toggleAfterDeadline(self):
    self.isAfterDeadline = not self.isAfterDeadline
    return self.isAfterDeadline
  
  def clearErrors(self):
    for id in self.mmgs:
      self.updateValue("disabled", False)
      self.updateValue("error", "")

    for id in self.reducers:
      self.updateValue("disabled", False)
      self.updateValue("error", "")

    return "Errors reset"


  def addMMG(self, name, url, author, tiles):
    id = secrets.token_hex(20)
    count = 0
    isUpdate = False
    late = False
    if self.isAfterDeadline:
      now = datetime.now()
      late = now.strftime("%H:%M:%S")
    
    # Check for existing MMG with same URL:
    for existingId in self.mmgs:
      if self.mmgs[existingId]["url"] == url:
        id = existingId
        count = self.mmgs[existingId]["count"]
        late = self.mmgs[existingId]["late"]
        isUpdate = True
        break

    mmg = {
      "id": id,
      "type": "mmg",
      "name": name,
      "url": url,
      "author": author,
      "tiles": tiles,
      "count": count,
      "late": late,
    }

    self.mmgs[id] = mmg
    if self.usingMongo:
      if isUpdate:
        self.collection_mmgs.replace_one({"id": id}, mmg)
      else:
        self.collection_mmgs.insert_one(mmg)
    
    print(f"✔️ Added MMG {name}: {url} by {author}")
    return mmg


  def addReducer(self, url, author):
    id = secrets.token_hex(20)
    count = 0
    isUpdate = False
    verification = None
    late = False
    if self.isAfterDeadline:
      now = datetime.now()
      late = now.strftime("%H:%M:%S")

    for existingId in self.reducers:
      if self.reducers[existingId]["url"] == url:
        id = existingId
        count = self.reducers[existingId]["count"]
        isUpdate = True
        verification = self.reducers[existingId]["verification"]
        late = self.reducers[existingId]["late"]
        break

    reducer = self.reducers[id] = {
      "id": id,
      "type": "reducer",
      "url": url,
      "author": author,
      "count": count,
      "verification": verification,
      "late": late,
    }

    if self.usingMongo:
      if isUpdate:
        self.collection_reducers.replace_one({"id": id}, reducer)
      else:
        self.collection_reducers.insert_one(reducer)

    print(f"✔️ Added reducer: {url} by {author}")
    return self.reducers[id]


  def saveUpdate(self, server, key):
    if not self.usingMongo:
      return

    updateQuery = {"$set": { key: server[key] }}
    if server["type"] == "mmg":
      self.collection_mmgs.update_one({"id": server["id"]}, updateQuery)
    else:
      self.collection_reducers.update_one({"id": server["id"]}, updateQuery)


  def updateCount(self, server):
    server["count"] += 1
    self.saveUpdate(server, "count")

  def updateValue(self, server, key, value):
    server[key] = value
    self.saveUpdate(server, key)
