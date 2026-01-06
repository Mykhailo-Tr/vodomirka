let currentFile = null;

const preview = document.getElementById("preview");
const processBtn = document.getElementById("processBtn");

const baseImg = document.getElementById("baseImg");
const idealImg = document.getElementById("idealImg");
const scoredImg = document.getElementById("scoredImg");

const shots = document.getElementById("shots");
const total = document.getElementById("total");
const jsonOut = document.getElementById("jsonOut");
const copyBtn = document.getElementById("copyBtn");

const modalImg = document.getElementById("modalImg");
const imgModal = document.getElementById("imgModal");

document.getElementById("fileInput").addEventListener("change", async e => {
  const file = e.target.files[0];
  if (!file) return;

  const form = new FormData();
  form.append("image", file);

  const res = await fetch("/upload", {
    method: "POST",
    body: form
  });

  const data = await res.json();
  currentFile = data.filename;

  preview.src = data.image_url;
  preview.classList.remove("d-none");

  baseImg.src = data.image_url;
  processBtn.disabled = false;
});

processBtn.onclick = async () => {
  // Save original button state
  const originalText = processBtn.innerHTML;
  const originalDisabled = processBtn.disabled;

  // Show spinner and update text
  processBtn.disabled = true;
  processBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Обробляється';

  try {
    const res = await fetch("/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: currentFile })
    });

    const data = await res.json();

    shots.innerText = data.stats.shots;
    total.innerText = data.stats.total_score;

    baseImg.src = data.images.overlay;
    idealImg.src = data.images.ideal;
    scoredImg.src = data.images.scored;

    jsonOut.textContent = JSON.stringify(data.json, null, 2);
  } catch (error) {
    console.error("Processing error:", error);
  } finally {
    // Restore button state
    processBtn.innerHTML = originalText;
    processBtn.disabled = originalDisabled;
  }
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

imgModal.onclick = () => {
  imgModal.classList.add("d-none");
};
