let currentFile = null;

document.getElementById("fileInput").addEventListener("change", async e => {
  const file = e.target.files[0];
  if (!file) return;

  const form = new FormData();
  form.append("image", file);

  const res = await fetch("/upload", { method: "POST", body: form });
  const data = await res.json();

  currentFile = data.filename;

  const img = document.getElementById("preview");
  img.src = data.image_url;
  img.classList.remove("d-none");

  document.getElementById("processBtn").disabled = false;
});

document.getElementById("processBtn").addEventListener("click", async () => {
  const res = await fetch("/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: currentFile })
  });

  const data = await res.json();

  document.getElementById("shots").innerText = data.stats.shots;
  document.getElementById("total").innerText = data.stats.total_score;

  document.getElementById("scoredImg").src = data.images.scored;
  document.getElementById("idealImg").src = data.images.ideal;

  document.getElementById("jsonOut").innerText =
    JSON.stringify(data.json, null, 2);

  document.getElementById("output").classList.remove("d-none");
});
