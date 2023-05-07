

import secrets


class ServersCollection:
  def __init__(self):
    self.mmgs = []
    self.reducers = []

  def addMMG(self, name, url, author, tiles):
    id = secrets.token_hex(20)
    count = 0
        
    # Check for existing MMG with same URL:
    for existingId in self.mmgs:
      if self.mmgs[existingId]["url"] == url:
        id = existingId
        count = self.mmgs[existingId]["count"]
        break

    self.mmgs[id] = {
      "id": id,
      "name": name,
      "url": url,
      "author": author,
      "tiles": tiles,
      "count": count,
    }

    return self.mmgs[id]

  def addReducer(self, url, author):
    id = secrets.token_hex(20)
    count = 0

    for existingId in self.reducers:
      if self.reducers[existingId]["url"] == url:
        id = existingId
        count = self.reducers[existingId]["count"]
        break

    self.reducers[id] = {
      "id": id,
      "url": url,
      "author": author,
      "type": "reducer",
      "count": count,
    }

    return self.reducers[id]

  
