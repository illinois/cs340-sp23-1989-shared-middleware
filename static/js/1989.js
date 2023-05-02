let doSubmit = async function () {
  let e = document.getElementById("image");
  let f = e.files[0];
  let tilesAcross = document.getElementById("tilesAcross").value;
  let renderedTileSize = document.getElementById("renderedTileSize").value;
  var data = new FormData();
  //set up jsConfetti
  const jsConfetti = new JSConfetti()
  //count how many mmgs are connected
  const response = await fetch('/api/serverCount');
  const countData = await response.json();
  const mmgCount = countData.count;
  data.append("image", f);
  data.append("tilesAcross", tilesAcross);
  data.append("renderedTileSize", renderedTileSize);

  /* SocketIO */
  var socket = io();
  socket.on('progress update', function (progress) {
    console.log("progress" + progress);
    progbar = document.getElementById("progbar");
    console.log(progbar.innerText)
    progbar.style.width = String(Math.round(Number(progress * 100))) + '%';
    progbar.setAttribute('aria-valuenow', Math.round(Number(progress * 100)));
    progbar.textContent = String(Math.round(Number(progress * 100))) + '%';
  });

  fetch("/makeMosaic", {
    method: "POST",
    body: data,
  })
  .then((response) => response.json())
  .then((json) => {
    const imageCount = json.length;
    console.log(imageCount)
    console.log(mmgCount)
    const diff = mmgCount- imageCount
    //if the number of connected servers is equal to the number of generated mosaics, confetti will continue to display for a second 🎉
    if (diff == 0) {
      console.log('no difference')
      setTimeout(() => {
        intervalId = setInterval(() => {
          jsConfetti.addConfetti();
        }, 100);
      }, 200);
      setTimeout(() => {
        clearInterval(intervalId);
      }, 1500)
    } else {
        //if any of the MMGs failed, it will show the number of failures with a sad face x2 😔
      setTimeout(() => {
        jsConfetti.addConfetti({confettiNumber: 400});
        jsConfetti.addConfetti({emojis:['😔'],confettiNumber: diff});
      }, 500);
    }

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
