// ============ أدوات عامة ============
async function postJSON(url, data) {
  const r = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data),
  });
  return r.json();
}
function el(id){ return document.getElementById(id); }
function htmlEscape(s){ return (s||"").replace(/[&<>"']/g, m=>({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[m])); }

// ============ البحث الرئيسي ============
async function doSearch(e){
  e.preventDefault();
  const ans = el("answer"); const srcs = el("sources"); const lat = el("latency");
  const qEl = el("q"); const chk = el("want_prices");
  if (!ans || !srcs || !qEl){ return; }
  ans.textContent = "… جاري البحث"; srcs.innerHTML = ""; if (lat) lat.textContent = "";
  const q = qEl.value.trim(); const want_prices = !!(chk && chk.checked);
  try{
    const t0 = performance.now();
    const res = await postJSON("/search", { q, want_prices });
    const dt = Math.round(performance.now() - t0);
    if(lat) lat.textContent = `الوقت: ${dt}ms`;
    if(!res.ok){ throw new Error(res.error || "search_failed"); }
    ans.textContent = res.answer || "—";
    srcs.innerHTML = (res.sources || []).map(
      s => `<a href="${s.url}" target="_blank" rel="noopener">${htmlEscape(s.title || s.url)}</a>`
    ).join("");
  }catch(err){
    ans.textContent = "حدث خطأ في البحث";
    if (lat) lat.textContent = "";
    console.error(err);
  }
}

// ============ بحث أشخاص / يوزرات (يدعم POST ثم GET كـ fallback) ============
async function doPeople(e){
  e.preventDefault();
  const nameInput = el("name");
  const out = el("profiles");
  if(!nameInput || !out){ return; }
  const name = nameInput.value.trim();
  out.innerHTML = "جارٍ البحث…";
  try{
    // نحاول POST أولاً
    let res = await postJSON("/people", { name });
    if (!res.ok){
      // لو فشل، نجرب GET (يساعد وقت مشاكل CORS أو Content-Type)
      const r = await fetch(`/people?name=${encodeURIComponent(name)}`);
      res = await r.json();
    }
    if(!res.ok){ throw new Error(res.error || "people_failed"); }
    if(!res.sources || res.sources.length === 0){
      out.innerHTML = "<span class='muted'>لا توجد نتائج.</span>";
      return;
    }
    out.innerHTML = res.sources.map(
      s => `<a href="${s.url}" target="_blank" rel="noopener">${htmlEscape(s.title || s.url)}</a>`
    ).join("");
  }catch(err){
    out.textContent = "حدث خطأ في بحث الأشخاص.";
    console.error(err);
  }
}

// ============ رفع PDF ============
async function doUploadPDF(e){
  e.preventDefault();
  const fileEl = el("pdfFile"); const out = el("pdfResult");
  if(!fileEl || !out){ return; }
  if(!fileEl.files || fileEl.files.length === 0){ out.textContent = "اختر ملفًا أولًا."; return; }
  out.textContent = "جارٍ الرفع…";
  try{
    const fd = new FormData(); fd.append("file", fileEl.files[0]);
    const r = await fetch("/upload_pdf", { method: "POST", body: fd });
    const data = await r.json();
    if(!data.ok){ throw new Error(data.error || "upload_failed"); }
    out.textContent = `${data.message} (الحروف: ${data.chars || 0})`;
  }catch(err){
    out.textContent = "فشل رفع الـ PDF.";
    console.error(err);
  }
}

// ============ رفع صورة + OCR ============
async function doUploadImg(e){
  e.preventDefault();
  const fileEl = el("imgFile"); const out = el("imgResult");
  if(!fileEl || !out){ return; }
  if(!fileEl.files || fileEl.files.length === 0){ out.textContent = "اختر صورة أولًا."; return; }
  out.textContent = "جارٍ الرفع…";
  try{
    const fd = new FormData(); fd.append("file", fileEl.files[0]);
    const r = await fetch("/upload_image", { method: "POST", body: fd });
    const data = await r.json();
    if(!data.ok){ throw new Error(data.error || "upload_failed"); }
    const txt = (data.text || "").trim();
    out.innerHTML = txt ? `<div class="answer">${htmlEscape(txt)}</div>` : "<span class='muted'>تم الرفع (لا نص مستخرج).</span>";
  }catch(err){
    out.textContent = "فشل رفع الصورة.";
    console.error(err);
  }
}

// ============ PWA: تثبيت ============
(function(){
  const btn = el("installBtn");
  if(!btn) return;
  let deferred;
  window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferred = e; btn.hidden = false; });
  btn.addEventListener("click", async () => { if(deferred){ deferred.prompt(); deferred = null; btn.hidden = true; }});
})();

// ============ تبديل المظهر ============
(function(){
  const btn = el("themeBtn");
  if(!btn) return;
  const apply = (m)=>{ document.body.classList.toggle("light", m==="light"); localStorage.setItem("theme", m); };
  apply(localStorage.getItem("theme") || "dark");
  btn.addEventListener("click", ()=> apply(document.body.classList.contains("light") ? "dark" : "light"));
})();

// ============ ربط الأحداث (مع دعم الاسمين profileForm/peopleForm) ============
(function init(){
  const searchForm  = el("searchForm");
  const profileForm = el("profileForm") || el("peopleForm"); // يدعم الاسمين
  const pdfForm     = el("pdfForm");
  const imgForm     = el("imgForm");

  if (searchForm)  searchForm.addEventListener("submit", doSearch);
  if (profileForm) profileForm.addEventListener("submit", doPeople);
  if (pdfForm)     pdfForm.addEventListener("submit", doUploadPDF);
  if (imgForm)     imgForm.addEventListener("submit", doUploadImg);
})();
