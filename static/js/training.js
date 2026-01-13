(function(){
  let session = null;
  let deletingImageId = null;
  let trainingChart = null;

  const ids = {
    athletesList: 'athletes-list',
    uploadBlock: 'uploadBlock',
    fileInput: 'file-input',
    uploadBtn: 'upload-btn',

    trainingPreview: 'trainingPreview',
    trainingCameraSelect: 'trainingCameraSelect',
    trainingCameraVideo: 'trainingCameraVideo',
    trainingCameraCanvas: 'trainingCameraCanvas',
    trainingCameraPreview: 'trainingCameraPreview',
    trainingCameraControls: 'trainingCameraControls',
    trainingCaptureBtn: 'trainingCaptureBtn',
    trainingStopCameraBtn: 'trainingStopCameraBtn',
    imagesList: 'images-list',
    sessionJson: 'session-json',
    sessionInfo: 'session-info',
    sessionAthletesList: 'session-athletes-list',
    statsShots: 'stat-shots',
    statsScore: 'stat-score',
    trainingChart: 'trainingChart',
    modalMainImg: 'modal-main-img',
    modalThumbs: 'modal-thumbs',
    modalShots: 'modal-shots',
    modalJson: 'modal-json',
    deleteModal: 'deleteModal',
    confirmDeleteBtn: 'confirm-delete-btn'
  };

  function $id(id){ return document.getElementById(id); }
  function q(sel,root=document){ return root.querySelector(sel); }

  function getSelectedAthletes(){
    return Array.from(document.querySelectorAll('.athlete-checkbox:checked')).map(cb=>parseInt(cb.value));
  }

  function clearMessages(){ const m = $id('upload-messages'); if(m) m.innerHTML=''; }
  function showMessage(msg, level='warning'){ const m = $id('upload-messages'); if(!m) return; m.innerHTML = `<div class="alert alert-${level} small mb-0">${msg}</div>`; setTimeout(()=>{ if(m) m.innerHTML=''; }, 8000); }

  async function startSession(){
    const btn = $id('start-session');
    if(!btn){
      console.error('Start session button not found');
      return;
    }
    const nameEl = $id('session-name');
    const name = (nameEl && nameEl.value) ? nameEl.value : 'Training';
    const selected = getSelectedAthletes();

    btn.disabled = true;
    clearMessages();
    try{
      console.log('Starting session with:', {name, athlete_ids: selected});
      const res = await fetch('/training/start', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({name, athlete_ids: selected})});
      console.log('Response status:', res.status, res.statusText);
      if(!res.ok){
        // try to parse json error
        let err = 'Failed to start session';
        try{ 
          const j = await res.json(); 
          if(j && j.error) err = j.error; 
          else if(j && j.message) err = j.message; 
        }catch(e){ 
          err = await res.text(); 
        }
        showMessage(err, 'danger');
        console.error('start session failed', err, res.status);
        return;
      }

      const data = await res.json();
      console.log('Session started:', data);
      session = data;
      updateSessionInfo();
      await refreshImages();
      showMessage('Session started', 'success');
    }catch(e){
      console.error('startSession error', e);
      showMessage('Error: ' + String(e), 'danger');
    }finally{ 
      if(btn) btn.disabled = false; 
    }
  }

  async function finishSession(){
    if(!session) return;
    await fetch(`/training/session/${session.id}/finish`, {method:'POST'});
    session = null;
    updateSessionInfo();
    await refreshImages();
  }

  function updateSessionInfo(){
    if(!session){
      const sessionInfoEl = $id(ids.sessionInfo);
      if(sessionInfoEl) sessionInfoEl.textContent = 'No session started';
      const sessionInfoRightEl = $id('session-info-right');
      if(sessionInfoRightEl) sessionInfoRightEl.textContent = 'No session started';
      const finishBtn = $id('finish-session');
      if(finishBtn) finishBtn.disabled = true;
      // show athlete selectors
      const athletesListEl = $id(ids.athletesList);
      if(athletesListEl) athletesListEl.classList.remove('d-none');
      const uploadBlockEl = $id(ids.uploadBlock);
      if(uploadBlockEl) uploadBlockEl.classList.add('d-none');
      const sessionAthletesListEl = $id(ids.sessionAthletesList);
      if(sessionAthletesListEl) sessionAthletesListEl.innerHTML = '';
    } else {
      const txt = `Session ${session.id} - ${session.name}`;
      const sessionInfoEl = $id(ids.sessionInfo);
      if(sessionInfoEl) sessionInfoEl.textContent = txt;
      const sessionInfoRightEl = $id('session-info-right');
      if(sessionInfoRightEl) sessionInfoRightEl.textContent = txt;
      const finishBtn = $id('finish-session');
      if(finishBtn) finishBtn.disabled = false;
      // hide athlete selectors and show which athletes were selected
      const athletesListEl = $id(ids.athletesList);
      if(athletesListEl) athletesListEl.classList.add('d-none');
      const selectedNames = Array.from(document.querySelectorAll('.athlete-checkbox:checked')).map(cb=>cb.nextElementSibling.textContent.trim());
      const sessionAthletesListEl = $id(ids.sessionAthletesList);
      if(sessionAthletesListEl) sessionAthletesListEl.textContent = selectedNames.join(', ') || '—';
      const uploadBlockEl = $id(ids.uploadBlock);
      if(uploadBlockEl) uploadBlockEl.classList.remove('d-none');

      // populate athlete filter dropdown
      const athleteList = document.getElementById('athlete-filter-list'); if(athleteList){ athleteList.innerHTML = '<label class="form-check"><input class="form-check-input chart-athlete-checkbox" type="checkbox" value="all" checked> All</label>'; const checks = document.querySelectorAll('.athlete-checkbox'); checks.forEach(cb=>{ const name = cb.nextElementSibling.textContent.trim(); const a = document.createElement('label'); a.className='form-check'; a.innerHTML = `<input class="form-check-input chart-athlete-checkbox" type="checkbox" value="${cb.value}"> ${name}`; athleteList.appendChild(a); });
      // bind change
      athleteList.querySelectorAll('.chart-athlete-checkbox').forEach(ch=> ch.addEventListener('change', ()=>{
        // if 'all' checked, uncheck others
        const all = Array.from(athleteList.querySelectorAll('.chart-athlete-checkbox')).find(x=>x.value==='all');
        if(all && all.checked){ athleteList.querySelectorAll('.chart-athlete-checkbox').forEach(x=>{ if(x.value!=='all') x.checked=false; }); }
        if(!all.checked){ // if any specific selected, uncheck all
          if(Array.from(athleteList.querySelectorAll('.chart-athlete-checkbox')).some(x=>x.value!=='all' && x.checked)) { all.checked = false; }
        }
        updateTrainingChart();
      })); }
    }
  }

  async function updateTrainingChart(providedImgs){
    if(!session) return;
    let imgs = providedImgs || null;
    if(!imgs){
        const r = await fetch(`/training/session/${session.id}/images`);
      imgs = await r.json();
    }

    const el = document.getElementById(ids.trainingChart);
    if(!el) return;

    // If user selected athlete filter(s), do grouping (ignore if 'all' checked)
    const athleteFilter = Array.from(document.querySelectorAll('.chart-athlete-checkbox:checked')).map(cb=>cb.value);
    if(athleteFilter && athleteFilter.length && !athleteFilter.includes('all')){
      // group images per athlete_id; create series per athlete
      const grouped = {};
      imgs.forEach(img=>{
        const aid = img.athlete_id || 'unassigned';
        if(!grouped[aid]) grouped[aid] = { name: img.athlete_name || (aid==='unassigned'?'Unassigned':'Athlete '+aid), imgs: [] };
        grouped[aid].imgs.push(img);
      });
      const series = Object.keys(grouped).filter(k=> athleteFilter.includes(String(k))).map(k=>({ name: grouped[k].name, data: grouped[k].imgs.map(i=>i.total_score||0), categories: grouped[k].imgs.map(i=>i.filename) }));
      // if no series after filter, show empty
      if(!series.length){ if(trainingChart) trainingChart.updateSeries([], true); return; }
      // if trainingChart not created, create multi-series chart
      if(!trainingChart){
        const opts = {
          chart: { type: 'area', height: 140, toolbar: { show: false } },
          series: series.map(s=>({ name: s.name, data: s.data })),
          xaxis: { categories: series[0] ? series[0].categories : [], labels: { rotate: -45 } },
          stroke: { curve: 'smooth' },
          colors: ['#0d6efd','#20c997','#fd7e14','#6f42c1','#dc3545'],
          tooltip: { enabled: true, custom: function({series, seriesIndex, dataPointIndex, w}){ const label = w.globals.labels[dataPointIndex]; return `<div class='small p-2'>${label}<br/>Score: ${series[seriesIndex][dataPointIndex]}</div>` } },
          dataLabels: { enabled: false }
        };
        trainingChart = new ApexCharts(el, opts);
        trainingChart.render();
      } else {
        trainingChart.updateOptions({ xaxis: { categories: series[0] ? series[0].categories : [] } }, false, false);
        trainingChart.updateSeries(series.map(s=>({ name: s.name, data: s.data })), true);
      }
      return;
    }
    const labels = imgs.map(i=> i.filename || (`#${i.id}`));
    const data = imgs.map(i=> i.total_score || 0);
    // map image filename -> shots for tooltip
    const shotsMap = {};
    imgs.forEach(i=>{ shotsMap[i.filename || (`#${i.id}`)] = i.shots || []; });
    if(!trainingChart){
      const opts = {
        chart: { type: 'area', height: 140, toolbar: { show: false } },
        series: [{ name: 'Total score', data }],
        xaxis: { categories: labels, labels: { rotate: -45 } },
        stroke: { curve: 'smooth' },
        colors: ['#0d6efd'],
        tooltip: { enabled: true, custom: function({series, seriesIndex, dataPointIndex, w}){
          const label = w.globals.labels[dataPointIndex];
          const shots = shotsMap[label] || [];
          if(!shots.length) return `<div class='small p-2'>${label}<br><em>No shots detected</em></div>`;
          const rows = shots.map(s=> `<div class='small'>#${s.id}: auto ${s.score || s.auto_score} final ${s.final_score || ''}</div>`).join('');
          return `<div class='p-2 small'><strong>${label}</strong><br/>Score: ${series[seriesIndex][dataPointIndex] || 0}<hr class="my-1"/>${rows}</div>`;
        }},
        dataLabels: { enabled: false }
      };
      trainingChart = new ApexCharts(el, opts);
      trainingChart.render();
    } else {
      trainingChart.updateOptions({ xaxis: { categories: labels } }, false, false);
      trainingChart.updateSeries([{ data }], true);
    }
  }

  async function uploadFile(){
    const f = $id('file-input').files[0];
    if(!f){ $id('upload-feedback').textContent='Choose a file first'; return; }
    if(!session){ $id('upload-feedback').textContent='Start a session first'; return; }

    // Show preview if available
    const preview = $id('upload-preview') || $id('trainingPreview');
    if(preview){
      const reader = new FileReader();
      reader.onload = e => { preview.src = e.target.result; preview.classList.remove('d-none'); };
      reader.readAsDataURL(f);
    }

    // disable buttons while working
    $id('upload-btn').disabled = true; if($id('snapshot-btn')) $id('snapshot-btn').disabled = true;
    clearMessages();
    try{
      const fd = new FormData(); fd.append('image', f);
      $id('upload-feedback').textContent='Uploading...';
      const r = await fetch('/upload', {method:'POST', body: fd});
      const j = await r.json();
      if(j.error){ $id('upload-feedback').textContent = j.error; showMessage(j.error, 'danger'); return; }
      $id('upload-feedback').textContent='Processing...';
      await processAndSave(j.filename);
    } finally {
      $id('upload-btn').disabled = false; if($id('snapshot-btn')) $id('snapshot-btn').disabled = false;
    }
  }

  async function processAndSave(filename){
    const r = await fetch('/process', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({filename})});
    const j = await r.json();
    if(j.error){ $id('upload-feedback').textContent = j.error; return; }

    // Save into training (use the full result object)
    const resultObj = (j && j.json) ? j.json : j;
    const savePayload = { session_id: session.id, filename: filename, result: resultObj };
    $id('upload-feedback').textContent = 'Saving result...';
    const save = await fetch('/training/save', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(savePayload)});
    const s = await save.json();
    if(s.error){ $id('upload-feedback').textContent = s.error; showMessage(s.error, 'danger'); return; }

    if(s.messages && s.messages.length){ s.messages.forEach(m=> showMessage(m, 'warning')); }

    $id('upload-feedback').textContent = `Saved image ${filename}`;
    // Refresh UI
    await refreshImages();

    // Update chart
    if(typeof updateTrainingChart==='function') updateTrainingChart();
  }

  async function snapshot(){
    // If camera stream is active, capture from it; otherwise try the app's cameraCapture or fallback to prompt
    let dataUrl = null;
    $id('upload-btn').disabled = true; if($id('snapshot-btn')) $id('snapshot-btn').disabled = true;
    clearMessages();
    try{
      if(typeof captureFromCamera === 'function' && document.querySelector('#trainingCameraPreview') && !document.querySelector('#trainingCameraPreview').classList.contains('d-none')){
        dataUrl = captureFromCamera();
      } else if(window.cameraCapture && typeof window.cameraCapture.capture === 'function'){
        dataUrl = await window.cameraCapture.capture();
      } else {
        dataUrl = prompt('Paste base64 data URL from camera (data:image/jpeg;base64,...)');
      }
      if(!dataUrl) return;
      $id('upload-feedback').textContent='Saving snapshot...';
      const res = await fetch('/snapshot', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({image: dataUrl})});
      const j = await res.json();
      if(j.error){ $id('upload-feedback').textContent = j.error; showMessage(j.error, 'danger'); return; }
      $id('upload-feedback').textContent='Processing snapshot...';
      await processAndSave(j.filename);
    } finally { $id('upload-btn').disabled = false; if($id('snapshot-btn')) $id('snapshot-btn').disabled = false; }
  }

  async function refreshImages(){
    if(!session) return;
    const r = await fetch(`/training/session/${session.id}/images`);
    const imgs = await r.json();
    const list = $id('images-list'); list.innerHTML='';
    let totalShots=0, totalScore=0;

    imgs.forEach(img=>{
      totalShots += img.shots_count || 0;
      totalScore += img.total_score || 0;
      const el = document.createElement('div'); el.className='list-group-item d-flex justify-content-between align-items-center';
      const viewBtn = `<button class="btn btn-sm btn-outline-primary me-1" data-action="view" data-id="${img.id}"><i class="bi bi-eye"></i></button>`;
      const delBtn = `<button class="btn btn-sm btn-danger" data-action="delete" data-id="${img.id}"><i class="bi bi-trash"></i></button>`;
      // If the session is finished, disallow deletes/uploads/edits - only view allowed
      const actionsHtml = (session && session.finished) ? `${viewBtn}` : `${viewBtn}${delBtn}`;

      el.innerHTML = `
        <div class="d-flex align-items-center">
          <img src="${img.overlay_path||img.scored_path||img.original_path}" style="width:80px;height:60px;object-fit:cover;border:1px solid #ddd;margin-right:10px;"/>
          <div>
            <strong class="d-block">${img.filename}</strong>
            <div class="small text-muted">${img.shots_count || 0} shots &middot; ${img.total_score || 0} pts ${img.athlete_name?`&middot; ${img.athlete_name}`:''}</div>
          </div>
        </div>
        <div class="text-end">
          <span class="badge bg-primary me-1"><i class="bi bi-bullseye me-1"></i>${img.shots_count || 0}</span>
          <span class="badge bg-success me-2"><i class="bi bi-star-fill me-1"></i>${img.total_score || 0}</span>
          ${actionsHtml}
        </div>
      `;
      list.appendChild(el);
      // clickable row (but ignore clicks on buttons)
      el.addEventListener('click', (e)=>{ if(e.target.closest('button')) return; openImageModal(img.id); });
    });

    $id('stat-shots').textContent = totalShots;
    $id('stat-score').textContent = totalScore;
    $id('session-json').textContent = JSON.stringify(imgs, null, 2);

    // attach handlers
    list.querySelectorAll('button[data-action="view"]').forEach(b=>b.addEventListener('click', ()=>openImageModal(b.dataset.id)));
    list.querySelectorAll('button[data-action="delete"]').forEach(b=>{
      b.addEventListener('click', ()=>{
        const id = b.dataset.id;
        // show confirmation modal
        $id('confirm-delete-btn').dataset.id = id;
        const delModalEl = document.getElementById('deleteModal'); let delModal = bootstrap.Modal.getInstance(delModalEl); if(!delModal) delModal = new bootstrap.Modal(delModalEl); delModal.show();
      });
    });

    // optionally update chart
    if(typeof updateTrainingChart==='function') updateTrainingChart(imgs);
  }

  async function openImageModal(id){
    const res = await fetch(`/training/image/${id}`);
    if(!res.ok) return;
    const img = await res.json();
    console.log('Image detail:', img);
    $id('imageModalLabel').textContent = img.filename || 'Image';
    $id('modal-json').textContent = JSON.stringify(img, null, 2);

    // show which image views are available in the modal footer (helpful for debugging)
    const availableKeys = ['overlay_path','scored_path','original_path','ideal_path'];
    const labels = {overlay_path:'Overlay', scored_path:'Scored', original_path:'Original', ideal_path:'Ideal'};
    const available = availableKeys.filter(k=>!!img[k]);
    const badgeHtml = available.length ? available.map(k=>`<span class="badge bg-secondary me-1">${labels[k]}</span>`).join(' ') : '<span class="small text-muted">No alternate views available</span>';
    $id('modal-image-filename').innerHTML = badgeHtml;

    const ms = $id('modal-shots'); ms.innerHTML='';
    (img.shots || []).forEach(sh => {
      const el = document.createElement('div'); el.className='list-group-item d-flex justify-content-between align-items-center align-items-center shot-row';
      const canEdit = !(session && session.finished);
      const editButtonsHtml = canEdit ? `<div class="d-flex gap-2"><button class="btn btn-sm btn-outline-primary" data-id="${sh.id}" data-action="edit">Edit</button><button class="btn btn-sm btn-outline-success" data-id="${sh.id}" data-action="inline-edit">Inline</button></div>` : '';
      el.innerHTML = `#${sh.id} - auto <strong>${sh.auto_score}</strong> / final <strong class="shot-final" data-id="${sh.id}">${sh.final_score || ''}</strong> ${editButtonsHtml}`;
      ms.appendChild(el);
    });

    if(!(session && session.finished)){
      ms.querySelectorAll('button[data-action="edit"]').forEach(b=>b.addEventListener('click', ()=>openShotModal(b.dataset.id)));
      ms.querySelectorAll('button[data-action="inline-edit"]').forEach(b=>b.addEventListener('click', async (e)=>{
        const id = e.currentTarget.dataset.id; const row = e.currentTarget.closest('.shot-row');
        // create inline editor
        const finalEl = row.querySelector('.shot-final'); const cur = finalEl.textContent.trim();
        finalEl.innerHTML = `<input type="number" class="form-control form-control-sm d-inline-block me-2" style="width:80px" value="${cur||0}" data-id="${id}" id="inline-score-${id}" /> <button class="btn btn-sm btn-primary" id="inline-save-${id}">Save</button>`;
        document.getElementById(`inline-save-${id}`).addEventListener('click', async ()=>{
          const v = parseInt(document.getElementById(`inline-score-${id}`).value) || 0;
          const r = await fetch(`/training/shot/${id}/edit`, {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({final_score: v, note: 'inline-edit'})});
          const j = await r.json(); if(j.ok){ finalEl.textContent = j.shot.final_score; showMessage('Shot updated', 'success'); await refreshImages(); updateTrainingChart(); }
        });
      }));
    }

    // thumbnails (show Overlay, Scored, Original, Ideal with labels and active highlighting)
    const thumbs = $id('modal-thumbs'); if(thumbs){
      thumbs.innerHTML='';
      const keys = ['overlay_path','scored_path','original_path','ideal_path'];
      const labels = {overlay_path:'Overlay', scored_path:'Scored', original_path:'Original', ideal_path:'Ideal'};
      let selectedKey = null;
      keys.forEach(k=>{
        if(img[k]){
          const fig = document.createElement('div'); fig.className = 'thumb-figure me-1 text-center';
          const im = document.createElement('img');
          im.src = img[k]; im.className = 'thumb-img'; im.style.cursor = 'pointer'; im.dataset.key = k; im.title = labels[k];
          im.addEventListener('click', ()=>{
            $id('modal-main-img').src = img[k];
            thumbs.querySelectorAll('.thumb-img').forEach(t=>t.classList.remove('active'));
            im.classList.add('active');
          });
          const cap = document.createElement('div'); cap.className = 'small text-muted'; cap.style.fontSize = '11px'; cap.textContent = labels[k];
          fig.appendChild(im); fig.appendChild(cap);
          thumbs.appendChild(fig);
          if(!selectedKey) selectedKey = k;
        }
      });
      // set default main image to first available (overlay -> scored -> original -> ideal)
      if(selectedKey){
        $id('modal-main-img').src = img[selectedKey];
        const active = thumbs.querySelector(`.thumb-img[data-key="${selectedKey}"]`);
        if(active) active.classList.add('active');
      } else {
        $id('modal-main-img').src = img.original_path || '';
      }
    }

    const imageModalEl = document.getElementById('imageModal'); let imageModal = bootstrap.Modal.getInstance(imageModalEl); if(!imageModal) imageModal = new bootstrap.Modal(imageModalEl); imageModal.show();
  }

  async function openShotModal(shotId){
    const r = await fetch(`/training/shot/${shotId}`);
    if(!r.ok) return;
    const sh = await r.json();
    $id('shot-details').innerHTML = `<pre>${JSON.stringify(sh, null, 2)}</pre>`;
    $id('shot-final-score').value = sh.final_score || sh.auto_score || 0;
    $id('shot-note').value = '';
    $id('save-shot-btn').dataset.id = shotId;
    const shotModalEl = document.getElementById('shotModal'); let shotModal = bootstrap.Modal.getInstance(shotModalEl); if(!shotModal) shotModal = new bootstrap.Modal(shotModalEl); shotModal.show();
  }

  async function saveShot(){
    const id = $id('save-shot-btn').dataset.id;
    const final = parseInt($id('shot-final-score').value) || 0;
    const note = $id('shot-note').value || '';
    const r = await fetch(`/training/shot/${id}/edit`, {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({final_score:final, note})});
    const j = await r.json();
    if(j.ok){
      await refreshImages();
      bootstrap.Modal.getInstance(document.getElementById('shotModal')).hide();
    }
  }

  async function deleteImageById(id){
    const btn = $id('confirm-delete-btn');
    if(btn) btn.disabled = true;
    try{
      const r = await fetch(`/training/image/${id}/delete`, {method:'POST'});
      const j = await r.json();
      if(j.ok){
        bootstrap.Modal.getInstance(document.getElementById('deleteModal')).hide();
        await refreshImages();
      } else if(j.error){
        $id('upload-feedback').textContent = j.error;
      }
    } catch(e){
      $id('upload-feedback').textContent = String(e);
    } finally {
      if(btn) btn.disabled = false;
    }
  }


  // convenience helper endpoint to fetch image shots (server side implementation missing - we add a quick handler below via a fetchback to /training/shot_sample)

  // Wire events
  document.addEventListener('DOMContentLoaded', ()=>{
    const startBtn = $id('start-session');
    if(startBtn){
      startBtn.addEventListener('click', startSession);
    } else {
      console.error('Start session button not found in DOM');
    }
    $id('finish-session').addEventListener('click', async ()=>{
      if(!session) return; await fetch(`/training/session/${session.id}/finish`, {method:'POST'}); session = null; updateSessionInfo(); await refreshImages();
    });

    $id('upload-btn').addEventListener('click', uploadFile);
    $id('save-shot-btn').addEventListener('click', saveShot);

    // delete modal confirm
    const confirmDeleteBtn = $id('confirm-delete-btn');
    if(confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', (e)=>{ deleteImageById(e.currentTarget.dataset.id); });

    // clear messages on modal close
    const delModalEl = document.getElementById('deleteModal'); if(delModalEl){ delModalEl.addEventListener('hidden.bs.modal', ()=> clearMessages()); }

    // file preview on choose
    const fileInput = $id('file-input');
    if(fileInput){ fileInput.addEventListener('change', ()=>{ const f = fileInput.files[0]; const prev = $id('upload-preview') || $id('trainingPreview'); if(f && prev){ const r = new FileReader(); r.onload=e=>{ prev.src=e.target.result; prev.classList.remove('d-none'); }; r.readAsDataURL(f);} }); }

    // Camera helpers
    let _trainingStream = null;
    async function enumerateCameras(){
      if(!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      const devices = await navigator.mediaDevices.enumerateDevices();
      const cams = devices.filter(d=>d.kind==='videoinput');
      const sel = $id(ids.trainingCameraSelect);
      if(!sel) return;
      sel.innerHTML = '<option value="">— Select camera —</option>' + cams.map(c=>`<option value="${c.deviceId}">${c.label || c.deviceId}</option>`).join('');
      if(cams.length){ sel.parentElement.classList.remove('d-none'); sel.value = cams[0].deviceId; }
    }
    async function startCamera(deviceId){
      try{
        await stopCamera();
        const constraints = {video: deviceId ? {deviceId: {exact: deviceId}} : {facingMode:'environment'}};
        _trainingStream = await navigator.mediaDevices.getUserMedia(constraints);
        const v = $id(ids.trainingCameraVideo);
        v.srcObject = _trainingStream;
        $id(ids.trainingCameraPreview).classList.remove('d-none');
        $id(ids.trainingCameraControls).classList.remove('d-none');
      } catch(e){ console.warn('camera start failed', e); }
    }
    async function stopCamera(){
      if(_trainingStream){ _trainingStream.getTracks().forEach(t=>t.stop()); _trainingStream = null; }
      $id(ids.trainingCameraPreview).classList.add('d-none');
      $id(ids.trainingCameraControls).classList.add('d-none');
    }
    function captureFromCamera(){
      const v = $id(ids.trainingCameraVideo); const c = $id(ids.trainingCameraCanvas);
      c.width = v.videoWidth; c.height = v.videoHeight; const ctx = c.getContext('2d'); ctx.drawImage(v,0,0); const dataUrl = c.toDataURL('image/jpeg', 0.9); return dataUrl;
    }

    // hook camera UI
    if($id(ids.trainingCameraSelect)){
      $id(ids.trainingCameraSelect).addEventListener('change', (e)=>{ if(e.target.value) startCamera(e.target.value); });
      $id('open-camera-btn').addEventListener('click', ()=>{ const sel = $id(ids.trainingCameraSelect); startCamera(sel && sel.value ? sel.value : null); });
      $id(ids.trainingCaptureBtn).addEventListener('click', async ()=>{ const data = captureFromCamera(); // show preview
        const prev = $id('trainingPreview'); if(prev){ prev.src = data; prev.classList.remove('d-none'); }
        // send to server same as snapshot flow
        $id('upload-feedback').textContent='Saving snapshot...';
        const res = await fetch('/snapshot', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({image: data})});
        const j = await res.json(); if(j.error){ $id('upload-feedback').textContent = j.error; return; }
        $id('upload-feedback').textContent='Processing snapshot...'; await processAndSave(j.filename);
      });
      $id(ids.trainingStopCameraBtn).addEventListener('click', ()=>stopCamera());
      // populate available cameras
      enumerateCameras();
    }

    // initial refresh if session exists
    // Hydrate preloaded session if provided by server (resume/view)
    if(window.PRELOADED_TRAINING_SESSION){
      try{ session = window.PRELOADED_TRAINING_SESSION; }catch(e){ session = null; }
      updateSessionInfo();
      if(session) refreshImages();
      // If session is finished, make UI read-only: hide upload block and disable edits
      if(session && session.finished){
        const uploadBlockEl = $id(ids.uploadBlock); if(uploadBlockEl) uploadBlockEl.classList.add('d-none');
        const startBtn = $id('start-session'); if(startBtn) startBtn.disabled = true;
        const finishBtn = $id('finish-session'); if(finishBtn) finishBtn.disabled = true;
      }
    } else {
      if(session) refreshImages();
    }
  });
})();