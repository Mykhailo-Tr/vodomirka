let currentFile = null;
let images = {};
let currentView = "original";

const fileInput = document.getElementById("fileInput");
const preview = document.getElementById("preview");
const processBtn = document.getElementById("processBtn");

const viewerBlock = document.getElementById("viewerBlock");
const viewerImage = document.getElementById("viewerImage");
const modalImg = document.getElementById("modalImg");

fileInput.addEventListener("change", async e => {
  const file = e.target.files[0];
  if (!file) return;

  const form = new FormData();
  form.append("image", file);

  const res = await fetch("/upload", { method: "POST", body: form });
  const data = await res.json();

  currentFile = data.filename;
  images.original = data.image_url;

  preview.src = data.image_url;
  preview.classList.remove("d-none");

  processBtn.disabled = false;
});

processBtn.addEventListener("click", async () => {
  const res = await fetch("/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: currentFile })
  });

  const data = await res.json();

  images.scored = data.images.scored;
  images.ideal = data.images.ideal;

  setView("scored");

  document.getElementById("shots").innerText = data.stats.shots;
  document.getElementById("total").innerText = data.stats.total_score;

  document.getElementById("thumbScored").src = images.scored;
  document.getElementById("thumbIdeal").src = images.ideal;

  document.getElementById("jsonOut").textContent =
    JSON.stringify(data.json, null, 2);

  document.getElementById("output").classList.remove("d-none");
  viewerBlock.classList.remove("d-none");
});

function setView(type) {
  if (!images[type]) return;
  currentView = type;
  viewerImage.src = images[type];
}

viewerImage.addEventListener("click", () => {
  modalImg.src = viewerImage.src;
});

function copyJSON() {
  navigator.clipboard.writeText(
    document.getElementById("jsonOut").textContent
  );
}
