(function(){
  // Simple sessions management UI
  const listEl = document.getElementById('sessions-list');
  const pagerEl = document.getElementById('sessions-pager');
  let currentPage = 1; const perPage = 10; let totalItems = 0;
  let pendingFinishId = null; let pendingDeleteId = null;

  async function fetchSessions(){
    const status = document.getElementById('filter-status').value;
    const athlete = document.getElementById('filter-athlete').value;
    const q = new URLSearchParams({page: currentPage, per_page: perPage});
    if(status) q.set('status', status);
    if(athlete) q.set('athlete_id', athlete);
    const res = await fetch('/training/api/sessions?' + q.toString());
    if(!res.ok) return;
    const j = await res.json(); totalItems = j.total; renderTable(j.items);
    renderPager(j.page, j.per_page, j.total);
  }

  function renderTable(items){
    if(!listEl) return;
    if(!items.length){ listEl.innerHTML = '<div class="p-3 text-muted">No sessions found.</div>'; return; }
    let html = '<table class="table table-sm table-hover"><thead><tr><th>#</th><th>Name</th><th>Athletes</th><th>Started</th><th>Finished</th><th>Status</th><th>Shots</th><th>Score</th><th>Actions</th></tr></thead><tbody>';
    items.forEach(s=>{
      const athletes = (s.athletes||[]).map(a=>a.name).join(', ');
      html += `<tr data-id="${s.id}"><td>${s.id}</td><td>${s.name||''}</td><td>${athletes}</td><td>${s.started_at||''}</td><td>${s.finished_at||''}</td><td>${s.status}</td><td>${s.total_shots||0}</td><td>${s.total_score||0}</td><td>`;
      if(s.status==='active'){
        html += `<button class="btn btn-sm btn-primary me-1" data-action="continue">Continue</button>`;
        html += `<button class="btn btn-sm btn-outline-danger me-1" data-action="finish">Finish</button>`;
      } else {
        html += `<button class="btn btn-sm btn-outline-secondary me-1" data-action="view">View</button>`;
      }
      html += `<button class="btn btn-sm btn-danger" data-action="delete">Delete</button>`;
      html += `</td></tr>`;
    });
    html += '</tbody></table>';
    listEl.innerHTML = html;
    // bind actions
    listEl.querySelectorAll('button[data-action="continue"]').forEach(b=> b.addEventListener('click', (e)=>{ const id = e.currentTarget.closest('tr').dataset.id; window.location.href = '/training/session/'+id; }));
    listEl.querySelectorAll('button[data-action="view"]').forEach(b=> b.addEventListener('click', (e)=>{ const id = e.currentTarget.closest('tr').dataset.id; window.location.href = '/training/session/'+id; }));
    listEl.querySelectorAll('button[data-action="finish"]').forEach(b=> b.addEventListener('click', (e)=>{ pendingFinishId = e.currentTarget.closest('tr').dataset.id; const modalEl = document.getElementById('confirmFinishModal'); let modal = bootstrap.Modal.getInstance(modalEl); if(!modal) modal = new bootstrap.Modal(modalEl); modal.show(); }));
    listEl.querySelectorAll('button[data-action="delete"]').forEach(b=> b.addEventListener('click', (e)=>{ pendingDeleteId = e.currentTarget.closest('tr').dataset.id; const modalEl = document.getElementById('confirmDeleteModal'); let modal = bootstrap.Modal.getInstance(modalEl); if(!modal) modal = new bootstrap.Modal(modalEl); modal.show(); }));
  }

  function renderPager(page, per_page, total){
    if(!pagerEl) return;
    const totalPages = Math.max(1, Math.ceil(total / per_page));
    let html = '<ul class="pagination">';
    for(let p=1;p<=totalPages;p++){
      html += `<li class="page-item ${p===page?'active':''}"><a class="page-link" href="#" data-page="${p}">${p}</a></li>`;
    }
    html += '</ul>';
    pagerEl.innerHTML = html;
    pagerEl.querySelectorAll('a.page-link').forEach(a=> a.addEventListener('click', (e)=>{ e.preventDefault(); currentPage = parseInt(a.dataset.page); fetchSessions(); }));
  }

  async function finishSession(){
    if(!pendingFinishId) return;
    const id = pendingFinishId; pendingFinishId = null;
    document.getElementById('confirm-finish-btn').disabled = true;
    try{
      const r = await fetch(`/training/session/${id}/finish`, {method:'POST'});
      if(r.ok){ const modalEl = document.getElementById('confirmFinishModal'); const modal = bootstrap.Modal.getInstance(modalEl); if(modal) modal.hide(); fetchSessions(); }
    }finally{ document.getElementById('confirm-finish-btn').disabled = false; }
  }

  async function deleteSession(){
    if(!pendingDeleteId) return;
    const id = pendingDeleteId; pendingDeleteId = null;
    document.getElementById('confirm-delete-session-btn').disabled = true;
    try{
      const r = await fetch(`/training/session/${id}/delete`, {method:'POST'});
      if(r.ok){ const modalEl = document.getElementById('confirmDeleteModal'); const modal = bootstrap.Modal.getInstance(modalEl); if(modal) modal.hide(); fetchSessions(); }
    }finally{ document.getElementById('confirm-delete-session-btn').disabled = false; }
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    document.getElementById('apply-filters').addEventListener('click', ()=>{ currentPage = 1; fetchSessions(); });
    document.getElementById('refresh-sessions').addEventListener('click', ()=> fetchSessions());
    document.getElementById('confirm-finish-btn').addEventListener('click', finishSession);
    document.getElementById('confirm-delete-session-btn').addEventListener('click', deleteSession);
    fetchSessions();
  });
})();
