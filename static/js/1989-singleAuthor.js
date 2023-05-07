var socket;

socket = io();
socket.on(`mosaic ${author}`, function (mosaicInfo) {
  var blob = new Blob( [ mosaicInfo.image ], { type: "image/png" } );
  var imageUrl = (window.URL || window.webkitURL).createObjectURL( blob );

  html = "";

  let e;
  if (mosaicInfo.tiles >= 0) {
    e = document.getElementById("mosaics");

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
  } else {
    e = document.getElementById("reduction");

    html += `<div class="col-2 mb-2">`;
    html += `<img src="${imageUrl}" class="img-fluid">`
    html += `<div style="font-size: 12px">`;
    html += `<b>Reduction</b><br>`;
    html += `<i>${mosaicInfo.description}<i>`;
    html += `</div>`;
    html += `</div>`;    
  }
  e.innerHTML += html;
  /*
  if (mosaicInfo.id == 1) {
    e.innerHTML = html;
  } else {
    e.innerHTML += html;
  }
  */
});

socket.on("connect", () => {
  fetch(`/testMosaic?author=${encodeURIComponent(author)}`)
  .then((response) => response.json())
  .then((json) => {
    if (json.error) {
      let e = document.getElementById("output");
      e.innerHTML =
        `<div class="alert alert-danger mb-3" role="alert"><h3>Mosaic Generation Error</h3>${json.error}</div>`
        + e.innerHTML;
    }
  });
})


let verify = function(how) {
  fetch(`/verify_${how}?author=${encodeURIComponent(author)}`)
  .then((response) => response.json())
  .then((json) => {
    let e = document.getElementById("verify");
    e.innerHTML = JSON.stringify(json);
  });
}