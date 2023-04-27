# Project 1989 Shared Middleware

## MMG Requirements

### MMG Registration Route: `PUT /addMMG` -> Middleware

Each MMG must register with the middleware to enable participation in the course-wide mosaic generation.  To register, send `PUT /addMMG` to the shared middleware with the following three required form variables:
- `name`, the name of your mosaic microservice generator
- `url`, the callback url for your mosaic microservice generator
- `author`, your name/netid

### MMG Mosaic Generation: Middleware -> `POST {url}`

A POST request will be sent to the `{url}` specified in the registration.  The `{url}` will be appended with a **query string** to include the two global parameters:
- `tilesAcross`, and
- `renderedTileSize`

Additionally, the base image will be sent as the file `image`.

(Refer to [Week #2](https://courses.grainger.illinois.edu/cs340/sp2023/project/week2/) for details on how these are used in your mosaic generation.)


## Mosaic Route: Frontend -> `POST /makeMosaic`

Initialize the mosaic creation process.

