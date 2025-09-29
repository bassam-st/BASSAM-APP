<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>بسّام الذكي v4.0</title>
<style>
  :root{
    --bg:#0b1020;--panel:#11162d;--bubble:#141b2e;--bubble-user:#1e2a50;
    --border:#223066;--text:#e7ecff;--accent:#4b6bff;--muted:#9fb3ff;--card:#0f1530;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);font-family:"Cairo",system-ui,Segoe UI,Arial}
  header{position:sticky;top:0;background:var(--panel);border-bottom:1px solid var(--border);padding:10px 14px;z-index:10}
  header .bar{max-width:1000px;margin:auto;display:flex;align-items:center;justify-content:space-between}
  h1{margin:0;font-size:18px;color:var(--muted)} h1 small{opacity:.8;font-weight:400}
  .wrap{max-width:1000px;margin:0 auto;padding:16px}
  /* Tabs */
  .tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
  .tab{padding:8px 12px;border:1px solid var(--border);border-radius:10px;background:#0f1733;cursor:pointer}
  .tab.active{background:var(--accent);color:#fff;border-color:transparent}
  .pane{display:none} .pane.active{display:block}
  /* Chat */
  .chat{display:flex;flex-direction:column;gap:10px;margin-bottom:100px}
  .msg{max-width:85%;padding:12px 14px;border-radius:14px;border:1px solid var(--border);background:var(--bubble);white-space:pre-wrap;line-height:1.8}
  .user{align-self:flex-start;background:var(--bubble-user)}
  .bot{align-self:flex-end}
  .footer{position:fixed;inset-inline:0;bottom:0;background:var(--panel);border-top:1px solid var(--border)}
  .send{max-width:1000px;margin:10px auto;display:flex;gap:8px;padding:0 16px}
  input[type=text]{flex:1;padding:12px;border-radius:12px;border:1px solid var(--border);background:#0f1a38;color:white}
  button{padding:12px 16px;border:none;border-radius:12px;background:var(--accent);color:white;font-weight:700;cursor:pointer}
  button:disabled{opacity:.6;cursor:not-allowed}
  a{color:#8fb1ff;word-break:break-all}
  .card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px;margin:8px 0}
  .mono{font-family:ui-monospace,Consolas,monospace;font-size:13px}
  .uploader{border:1px dashed var(--border);border-radius:12px;padding:14px;background:#0f1733}
  .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  .muted{opacity:.75}
  .grid{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
  .btn-sm{padding:6px 10px;border-radius:10px;background:#17306f;border:1px solid #2a3b76;color:#fff;cursor:pointer}
  /* تفاصيل (لوحة جانبية) */
  .drawer{position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;align-items:stretch;z-index:50}
  .drawer.open{display:flex}
  .drawer-panel{margin-inline-start:auto;width:min(760px,100%);height:100%;background:#0b122a;border-left:1px solid #223066;display:flex;flex-direction:column}
  .drawer-header{padding:12px 14px;border-bottom:1px solid #223066;display:flex;justify-content:space-between;align-items:center}
  .drawer-body{padding:14px;overflow:auto}
  .chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
  .chip{padding:6px 10px;border-radius:999px;background:#111c3d;border:1px solid #274086;font-size:12px}
  .actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
</style>
</head>
<body>
<header>
  <div class="bar">
    <h1>🤖 بسّام الذكي <small>v4.0</small></h1>
    <div style="font-size:13px" class="muted">دردشة • بحث متقدّم • PDF • بحث عكسي بالصور • تنزيل</div>
  </div>
</header>

<div class="wrap">
  <div class="tabs">
    <div class="tab active" data-pane="chat">الدردشة</div>
    <div class="tab" data-pane="pdf">رفع PDF</div>
    <div class="tab" data-pane="image">بحث عكسي بصورة</div>
    <div class="tab" onclick="window.open('/files_list','_blank')">📂 ملفاتي</div>
    <div class="tab" onclick="window.open('/healthz','_blank')">الصحة</div>
  </div>

  <!-- CHAT -->
  <section id="pane-chat" class="pane active">
    <div id="chat" class="chat">
      <div class="msg bot">
        أهلًا! اكتب سؤالك وسأبدأ بملفاتك (RAG) ثم الويب ثم الرياضيات.
        <div class="muted">أمثلة: “ما هي الخرسانة المسلحة؟” • “تفاضل x^3” • “ابحث في الويب عن عاصمة ألمانيا”</div>
      </div>
    </div>
    <div class="footer">
      <div class="send">
        <input id="q" type="text" placeholder="اكتب سؤالك هنا… ثم اضغط إرسال أو Enter" onkeydown="if(event.key==='Enter'){send()}" />
        <button id="btn" onclick="send()">إرسال</button>
      </div>
    </div>
  </section>

  <!-- PDF -->
  <section id="pane-pdf" class="pane">
    <div class="uploader">
      <div class="row">
        <input id="pdf" type="file" accept="application/pdf" />
        <button onclick="uploadPDF()">رفع و فهرسة</button>
      </div>
      <div id="pdf-result" class="card mono"></div>
      <small class="muted">بعد الرفع يُستخرج النص من PDF ويُضاف تلقائيًا إلى فهرس RAG.</small>
    </div>
  </section>

  <!-- IMAGE -->
  <section id="pane-image" class="pane">
    <div class="uploader">
      <div class="row">
        <input id="img" type="file" accept="image/*" capture="environment" />
        <button onclick="uploadImage()">رفع صورة</button>
      </div>
      <div id="img-result" class="card"></div>
      <small class="muted">سأعطيك روابط بحث عكسي جاهزة (Google/Bing/Yandex/TinEye) للصورة المرفوعة، ويمكن تنزيلها.</small>
    </div>
  </section>
</div>

<!-- لوحة التفاصيل -->
<div id="drawer" class="drawer" onclick="if(event.target===this) closeDrawer()">
  <div class="drawer-panel">
    <div class="drawer-header">
      <b>التفاصيل الكاملة</b>
      <button class="btn-sm" onclick="closeDrawer()">إغلاق</button>
    </div>
    <div class="drawer-body">
      <div id="detail-answer" class="card"></div>
      <div id="detail-sources"></div>
    </div>
  </div>
</div>

<script>
/* ---------- Tabs ---------- */
document.querySelectorAll('.tab[data-pane]').forEach(t=>{
  t.addEventListener('click', ()=>{
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    const id=t.dataset.pane;
    document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
    document.getElementById('pane-'+id).classList.add('active');
  });
});

/* ---------- Chat helpers ---------- */
const chat = document.getElementById('chat');
const qbox = document.getElementById('q');
const btn  = document.getElementById('btn');

function escapeHTML(s){return (s||'').replace(/[&<>"]/g,m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]))}
function mdLite(s){ return (s||'').replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/\n/g,'<br>'); }

function addMine(text){
  const div=document.createElement('div');
  div.className='msg user';
  div.textContent=text;
  chat.appendChild(div);
  window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'});
}

function addBotPreview(fullText, sources){
  const preview = makePreview(fullText, 420); // طول مناسب للفقاعة
  const box=document.createElement('div');
  box.className='msg bot';
  box.innerHTML = `<div>${mdLite(escapeHTML(preview))}</div>`;
  const actions=document.createElement('div');
  actions.className='actions';
  const moreBtn=document.createElement('button');
  moreBtn.className='btn-sm';
  moreBtn.textContent='عرض التفاصيل';
  moreBtn.onclick=()=>openDrawer(fullText, sources);
  actions.appendChild(moreBtn);

  // لو فيه مصادر، زر سريع لفتح أول مصدر
  if(sources && sources.length){
    const openFirst=document.createElement('a');
    openFirst.className='btn-sm';
    openFirst.textContent='فتح أول مصدر';
    openFirst.href=sources[0].link;
    openFirst.target='_blank';
    actions.appendChild(openFirst);
  }
  box.appendChild(actions);
  chat.appendChild(box);
  window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'});
}

function makePreview(s, max=420){
  s = (s||'').trim();
  if(s.length<=max) return s;
  // قص ذكي عند حدود الجملة
  const cut = s.slice(0, max);
  const lastDot = Math.max(cut.lastIndexOf('。'), cut.lastIndexOf('؟'), cut.lastIndexOf('?'), cut.lastIndexOf('،'), cut.lastIndexOf('.'));
  return (lastDot>120 ? cut.slice(0,lastDot+1) : cut) + ' …';
}

function addNote(text){
  const div=document.createElement('div');
  div.className='msg bot';
  div.textContent=text;
  chat.appendChild(div);
  window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'});
  return div;
}

function showSourcesFull(results){
  if(!results||!results.length) return '<div class="muted">لا توجد مصادر.</div>';
  return results.map(s=>{
    const isPDF = /\.pdf(\?|$)/i.test(s.link||'');
    const name  = (s.title || s.link || 'مصدر').slice(0,120);
    return `
      <div class="card">
        <div class="chips"><span class="chip">${escapeHTML((s.domain||'').replace(/^www\./,''))}</span></div>
        <b>${escapeHTML(name)}</b><br>
        <a href="${s.link}" target="_blank">${s.link}</a>
        <div class="muted" style="margin-top:6px">${escapeHTML(s.summary||s.snippet||'')}</div>
        <div class="actions">
          <a class="btn-sm" target="_blank" href="${s.link}">فتح</a>
          <button class="btn-sm" onclick="downloadFile('${s.link.replace(/'/g,'\\\'')}', '${isPDF?'document.pdf':'file'}')">تنزيل</button>
        </div>
      </div>`;
  }).join('');
}

/* ---------- Drawer (تفاصيل) ---------- */
const drawer = document.getElementById('drawer');
const detailAnswer = document.getElementById('detail-answer');
const detailSources = document.getElementById('detail-sources');

function openDrawer(fullText, sources){
  detailAnswer.innerHTML = mdLite(escapeHTML(fullText || ''));
  detailSources.innerHTML = sources ? ('<h4>المصادر</h4>' + showSourcesFull(sources)) : '';
  drawer.classList.add('open');
}
function closeDrawer(){ drawer.classList.remove('open'); }

/* ---------- Ask ---------- */
async function send(){
  const q=(qbox.value||'').trim();
  if(!q) return;
  addMine(q); qbox.value=''; qbox.focus();
  const wait=addNote('⏳ جاري المعالجة…');

  btn.disabled=true;
  try{
    const res=await fetch('/ask?q='+encodeURIComponent(q));
    const j=await res.json();
    wait.remove();

    // الخادم يُرجع: {type:"chat", answer:"…", sources:[…]} أو math/web/rag
    if(j.type==='math' && j.answer){
      addBotPreview(j.answer); // هي نفسها ملخص محسّن
    }else if(j.answer){
      addBotPreview(j.answer, j.sources||j.results||j.hits||[]);
    }else if(j.msg){
      addBotPreview(j.msg);
    }else{
      addBotPreview('لم أفهم الرد.');
    }
  }catch(e){
    wait.remove();
    addBotPreview('⚠️ حدث خطأ بالاتصال.');
  }finally{
    btn.disabled=false;
  }
}

/* ---------- Upload PDF ---------- */
async function uploadPDF(){
  const inp=document.getElementById('pdf');
  const box=document.getElementById('pdf-result');
  if(!inp.files.length){ box.textContent='اختر ملف PDF أولًا.'; return; }
  const fd=new FormData(); fd.append('file', inp.files[0]);
  box.textContent='⏳ جاري الرفع والفهرسة...';
  try{
    const res=await fetch('/upload/pdf',{method:'POST',body:fd});
    const j=await res.json();
    box.innerHTML='<b>تم الرفع ✔️</b><br>الرابط: <a target="_blank" href="'+j.file_url+'">'+j.file_url+
      '</a> <button class="btn-sm" onclick="downloadFile(\''+j.file_url+'\', \'document.pdf\')">تنزيل</button>'+
      '<br>عدد المستندات في الفهرس: '+j.indexed_docs;
  }catch(e){
    box.textContent='فشل الرفع.';
  }
}

/* ---------- Upload Image + reverse search ---------- */
async function uploadImage(){
  const inp=document.getElementById('img');
  const box=document.getElementById('img-result');
  if(!inp.files.length){ box.textContent='اختر صورة أولًا.'; return; }
  const fd=new FormData(); fd.append('file', inp.files[0]);
  box.textContent='⏳ جاري الرفع...';
  try{
    const res=await fetch('/upload/image',{method:'POST',body:fd});
    const j=await res.json();
    const links = [
      {title:'Google Images', link:j.reverse.google, snippet:'بحث عكسي على Google'},
      {title:'Bing',          link:j.reverse.bing,   snippet:'بحث عكسي على Bing'},
      {title:'Yandex',        link:j.reverse.yandex, snippet:'بحث عكسي على Yandex'},
      {title:'TinEye',        link:j.reverse.tineye, snippet:'بحث عكسي على TinEye'}
    ];
    box.innerHTML = `
      <div>تم الرفع ✔️ — <a target="_blank" href="${j.image_url}">فتح الصورة</a>
      <button class="btn-sm" onclick="downloadFile('${j.image_url}', 'image')">تنزيل</button></div>
      <div class="card">${showSourcesFull(links)}</div>`;
  }catch(e){
    box.textContent='فشل الرفع.';
  }
}

/* ---------- Backend proxy download ---------- */
async function downloadFile(url, suggestedName="file"){
  try{
    const r = await fetch('/download?url=' + encodeURIComponent(url));
    if(!r.ok) throw new Error('DL failed');
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = suggestedName;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(a.href);
  }catch(e){ alert('فشل التنزيل'); }
}

/* ---------- Enter key on chat ---------- */
qbox.addEventListener('keydown', e=>{ if(e.key==='Enter'){ send(); } });
</script>
</body>
</html>
