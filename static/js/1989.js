var socket;

let doSubmit = function () {
  document.getElementById("output").innerHTML = `<div id="mosaics" class="row"></div>`;

  let e = document.getElementById("image");
  let f = e.files[0];
  let tilesAcross = document.getElementById("tilesAcross").value;
  let renderedTileSize = document.getElementById("renderedTileSize").value;
  var data = new FormData();
  data.append("image", f);
  data.append("tilesAcross", tilesAcross);
  data.append("renderedTileSize", renderedTileSize);

  /* SocketIO */
  if (!socket) {
    socket = io();
    socket.on('progress update', function (progress) {
      progbar = document.getElementById("progbar");
      progbar.style.width = String(Math.round(Number(progress * 100))) + '%';
      progbar.setAttribute('aria-valuenow', Math.round(Number(progress * 100)));
      progbar.textContent = String(Math.round(Number(progress * 100))) + '%';
    });
  
    socket.on('mosaic', function (mosaicInfo) {   
      var blob = new Blob( [ mosaicInfo.image ], { type: "image/png" } );
      var imageUrl = (window.URL || window.webkitURL).createObjectURL( blob );
  
      html = "";
      html += `<div class="col-2">`;
      html += `<img src="${imageUrl}" class="img-fluid">`
      html += `<div style="font-size: 12px">`;
      html += `<b>Mosaic #${mosaicInfo.id}</b><br>`;
      html += `<i>${mosaicInfo.description}<i>`;
      html += `</div>`;
      html += `</div>`;
  
      let e = document.getElementById("mosaics");
      e.innerHTML += html;
    });
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
