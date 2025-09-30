async function jsonFetch(url, options){
  const r = await fetch(url, options); if(!r.ok) throw new Error('network'); return r.json();
}

// search
document.getElementById('searchForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const q = document.getElementById('q').value.trim();
  const want_prices = document.getElementById('want_prices').checked;
  const out = await jsonFetch(`/api/search?q=${encodeURIComponent(q)}&want_prices=${want_prices}`);
  document.getElementById('answer').textContent = out.answer || '';
  const src = document.getElementById('sources'); src.innerHTML = '';
  (out.sources||[]).forEach(s=>{ const a = document.createElement('a'); a.href=s.url; a.target='_blank'; a.textContent=`${s.site} — ${s.title}`; src.appendChild(a); });
  if(out.prices){ const h = document.createElement('div'); h.innerHTML = '<h4>الأسعار</h4>'; src.appendChild(h); out.prices.forEach(p=>{ const a=document.createElement('a'); a.href=p.url; a.target='_blank'; a.textContent=p.site; src.appendChild(a); }); }
});

// pdf upload
document.getElementById('pdfForm').addEventListener('submit', async (e)=>{
  e.preventDefault(); const f = document.getElementById('pdfFile').files[0]; if(!f) return;
  const fd = new FormData(); fd.append('file', f);
  const out = await jsonFetch('/api/upload/pdf', { method:'POST', body: fd });
  document.getElementById('pdfResult').textContent = out.ok ? `تم رفعه وفهرسته: ${out.indexed_file}` : 'فشل الرفع';
});

// image upload + reverse image links
document.getElementById('imgForm').addEventListener('submit', async (e)=>{
  e.preventDefault(); const f = document.getElementById('imgFile').files[0]; if(!f) return;
  const fd = new FormData(); fd.append('file', f);
  const out = await jsonFetch('/api/search_image', { method:'POST', body: fd });
  const box = document.getElementById('imgResult'); box.innerHTML = '';
  const img = document.createElement('img'); img.src = out.image_url; img.style.maxWidth='180px'; img.style.borderRadius='12px'; box.appendChild(img);
  (out.links||[]).forEach(l=>{ const a=document.createElement('a'); a.href=l.url; a.target='_blank'; a.textContent=l.name; box.appendChild(a); });
});
