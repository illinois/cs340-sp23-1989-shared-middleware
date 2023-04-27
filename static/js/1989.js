let doSubmit = function () {
  let e = document.getElementById("image");
  let f = e.files[0];
  let tilesAcross = document.getElementById("tilesAcross").value;
  let renderedTileSize = document.getElementById("renderedTileSize").value;
  var data = new FormData();
  data.append("image", f);
  data.append("tilesAcross", tilesAcross);
  data.append("renderedTileSize", renderedTileSize);
  fetch("/makeMosaic/", {
    method: "POST",
    body: data,
  })
  .then((response) => response.json())
  .then((json) => {
    let html = "";

    html += `<div class="row">`;
    for (let d of json) {
      html += `<div class="col-2"><img src="${d.image}" class="img-fluid"></div>`;
    }
    html += `</div>`;

    let e = document.getElementById("mosaics");
    e.innerHTML = html;
  });
};
