var socket;
socket = io();
socket.on('progress update', function (d) {
  let pct = (d.current / d.total) * 100;

  e = document.getElementById("progbar");
  e.style.width = `${Math.round(pct)}%`
  e.setAttribute('aria-valuenow', Math.round(pct));
  e.textContent = `${d.current} of ${d.total} -- ${Math.round(pct)}%`
});

socket.on('mosaic', function (mosaicInfo) {
  var blob = new Blob( [ mosaicInfo.image ], { type: "image/png" } );
  var imageUrl = (window.URL || window.webkitURL).createObjectURL( blob );

  html = "";
  html += `<div class="col-2 mb-2">`;
  html += `<img src="${imageUrl}" class="img-fluid">`
  html += `<div style="font-size: 12px">`;
  html += `<b>Mosaic #${mosaicInfo.id}</b> (${mosaicInfo.tiles} tiles`;
  if (mosaicInfo.mosaics > 1) {
    html += `; ${mosaicInfo.mosaics} mosaics)<br>`;
  } else {
    html += `)<br>`;
  }
  html += `<i>${mosaicInfo.description}<i>`;
  html += `</div>`;
  html += `</div>`;

  let e = document.getElementById("mosaics");
  e.innerHTML += html;
  /*
  if (mosaicInfo.id == 1) {
    e.innerHTML = html;
  } else {
    e.innerHTML += html;
  }
  */
});


let doSubmit = function () {
  document.getElementById("output").innerHTML = `<div id="mosaics" class="row"></div>`;

  let e = document.getElementById("image");
  let f = e.files[0];
  let tilesAcross = document.getElementById("tilesAcross").value;
  let renderedTileSize = document.getElementById("renderedTileSize").value;
  let fileFormat = document.getElementById("fileFormat").value;
  let filter = document.getElementById("filter").value;
  let verifiedOnly = document.getElementById("verified").checked;

  var data = new FormData();
  data.append("image", f);
  data.append("tilesAcross", tilesAcross);
  data.append("renderedTileSize", renderedTileSize);
  data.append("fileFormat", fileFormat);
  data.append("filter", filter);
  if (verifiedOnly) {
    data.append("verified", "true");
  }

  fetch("/makeMosaic", {
    method: "POST",
    body: data,
  })
  .then((response) => response.json())
  .then((json) => {
    if (json.error) {
      let e = document.getElementById("output");
      e.innerHTML =
        `<div class="alert alert-danger mb-3" role="alert"><h3>Mosaic Generation Error</h3>${json.error}</div>`
        + e.innerHTML;
    }
  });
};
