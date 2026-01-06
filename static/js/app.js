let currentFile = null;

const preview = document.getElementById("preview");
const processBtn = document.getElementById("processBtn");

const idealCheck = document.getElementById("idealCheck");
const scoredCheck = document.getElementById("scoredCheck");

const idealOverlay = document.getElementById("idealOverlay");
const scoredOverlay = document.getElementById("scoredOverlay");

document.getElementById("fileInput").addEventListener("change", async e => {
  const file = e.target.files[0];
  if (!file) return;

  const form = new FormData();
  form.append("image", file);

  const res = await fetch("/upload", { method: "POST", body: form });
  const data = await res.json();

  currentFile = data.filename;

  preview.src = data.image_url;
  preview.classList.remove("d-none");

  document.getElementById("baseImg").src = data.image_url;

  processBtn.disabled = false;
});

processBtn.onclick = async () => {
  const res = await fetch("/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: currentFile })
  });

  const data = await res.json();

  shots.innerText = data.stats.shots;
  total.innerText = data.stats.total_score;

  idealImg.src = data.images.ideal;
  scoredImg.src = data.images.scored;

  idealOverlay.src = data.images.ideal;
  scoredOverlay.src = data.images.scored;

  jsonOut.textContent = JSON.stringify(data.json, null, 2);
};

// Overlay toggles
idealCheck.onchange = () => {
  idealOverlay.classList.toggle("d-none", !idealCheck.checked);
};

scoredCheck.onchange = () => {
  scoredOverlay.classList.toggle("d-none", !scoredCheck.checked);
};

// Copy JSON
copyBtn.onclick = () => {
  navigator.clipboard.writeText(jsonOut.textContent);
  copyBtn.innerText = "✔ Copied";
  setTimeout(() => copyBtn.innerText = "Copy", 2000);
};

// Modal viewer
document.addEventListener("click", e => {
  if (e.target.tagName !== "IMG" || !e.target.src) return;
  modalImg.src = e.target.src;
  imgModal.classList.remove("d-none");
});

imgModal.onclick = () => imgModal.classList.add("d-none");
