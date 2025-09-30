async function jsonFetch(url, options){
  const r = await fetch(url, options);
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}

// ===== Theme (light/dark)
const themeBtn = document.getElementById('themeBtn');
function applyTheme(t){ document.body.classList.toggle('light', t==='light'); localStorage.setItem('theme', t); }
applyTheme(localStorage.getItem('theme') || 'dark');
themeBtn.addEventListener('click', ()=> applyTheme(document.body.classList.contains('light') ? 'dark' : 'light'));

// ===== PWA install
let deferredPrompt; const installBtn = document.getElementById('installBtn');
window.addEventListener('beforeinstallprompt', (e)=>{ e.preventDefault(); deferredPrompt = e; installBtn.hidden = false; });
installBtn.addEventListener('click', async ()=>{
  if(!deferredPrompt) return; await deferredPrompt.prompt(); deferredPrompt = null; installBtn.hidden = true;
});

// ===== Search
const ans = document.getElementById('answer');
const src = document.getElementById('sources');
const latencyEl = document.getElementById('latency');

document.getElementById('searchForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const q = document.getElementById('q').value.trim();
  const want_prices = document.getElementById('want_prices').checked;
  if(!q) return;

  ans.textContent = '… يبحث الآن';
  src.innerHTML = '';
  const t0 = performance.now();
  try {
    const out = await jsonFetch(`/api/search?q=${encodeURIComponent(q)}&want_prices=${want_prices}`);
    const t1 = performance.now();
    latencyEl.textContent = `الزمن: ${Math.round(t1 - t0)}ms`;
    ans.textContent = out.answer || '';
    (out.sources||[]).forEach(s=>{
      const a = document.createElement('a'); a.href = s.url; a.target = '_blank'; a.textContent = `${s.site} — ${s.title}`; src.appendChild(a);
    });
    if(out.prices){
      const h = document.createElement('div'); h.innerHTML = '<h4>الأسعار</h4>'; src.appendChild(h);
      out.prices.forEach(p=>{ const a=document.createElement('a'); a.href=p.url; a.target='_blank'; a.textContent=p.site; src.appendChild(a); });
    }
    // بعد نجاح البحث سجّل حدث تعلّم سريع محليًا (اختياري على الباك-إند)
    try {
      const fd = new FormData(); fd.append('query', q); fd.append('top_k', '3');
      await fetch('/api/learn', { method:'POST', body: fd }); // لا ننتظر النتيجة
    } catch {}
  } catch (err) {
    ans.textContent = 'حدث خطأ في البحث'; console.log(err);
  }
});

// ===== Learn button (صريح)
document.getElementById('learnBtn').addEventListener('click', async (e)=>{
  e.preventDefault();
  const q = document.getElementById('q').value.trim(); if(!q) return;
  const fd = new FormData(); fd.append('query', q); fd.append('top_k','3');
  try { await fetch('/api/learn', { method:'POST', body: fd }); alert('تم تحديث ذاكرة بسام من هذا البحث ✅'); } catch {}
});

// ===== Profile / username lookup
document.getElementById('profileForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const name = document.getElementById('name').value.trim(); if(!name) return;
  const out = await jsonFetch(`/api/profile?name=${encodeURIComponent(name)}`);
  const box = document.getElementById('profiles'); box.innerHTML = '';
  (out.links||[]).forEach(l=>{ const a=document.createElement('a'); a.href=l.url; a.target='_blank'; a.textContent=l.site; box.appendChild(a); });
  (out.web||[]).forEach(w=>{ const a=document.createElement('a'); a.href=w.url; a.target='_blank'; a.textContent=w.title || w.url; box.appendChild(a); });
});

// ===== PDF upload
document.getElementById('pdfForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const f = document.getElementById('pdfFile').files[0]; if(!f) return;
  const fd = new FormData(); fd.append('file', f);
  const out = await jsonFetch('/api/upload/pdf', { method:'POST', body: fd });
  document.getElementById('pdfResult').textContent = out.ok ? `تمت الفهرسة: ${out.indexed_file}` : 'فشل الرفع';
});

// ===== Image upload + reverse image links
document.getElementById('imgForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const f = document.getElementById('imgFile').files[0]; if(!f) return;
  const fd = new FormData(); fd.append('file', f);
  const out = await jsonFetch('/api/search_image', { method:'POST', body: fd });
  const box = document.getElementById('imgResult'); box.innerHTML = '';
  const img = document.createElement('img'); img.src = out.image_url; img.style.maxWidth='180px'; img.style.borderRadius='12px'; box.appendChild(img);
  (out.links||[]).forEach(l=>{ const a=document.createElement('a'); a.href=l.url; a.target='_blank'; a.textContent=l.name; box.appendChild(a); });
});
