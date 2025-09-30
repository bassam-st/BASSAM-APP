async function postJSON(url, data) {
  const r = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  });
  return r.json();
}

function el(id){ return document.getElementById(id); }

async function doSearch(e){
  e.preventDefault();
  el("answer").textContent = "… جاري البحث";
  el("sources").innerHTML = "";
  const q = el("q").value.trim();
  const want_prices = el("want_prices").checked;
  try{
    const res = await postJSON("/search", { q, want_prices });
    if(!res.ok){ throw new Error(res.error || "search_failed"); }
    el("latency").textContent = `الوقت: ${res.latency_ms}ms`;
    el("answer").textContent = res.answer || "—";
    el("sources").innerHTML = (res.sources || []).map(
      s => `<a href="${s.url}" target="_blank" rel="noreferrer">${s.title || s.url}</a>`
    ).join("");
  }catch(err){
    el("answer").textContent = "حدث خطأ في البحث";
    console.error(err);
  }
}

async function doPeople(e){
  e.preventDefault();
  el("profiles").innerHTML = "…";
  const name = el("name").value.trim();
  try{
    const res = await postJSON("/people", { name });
    if(!res.ok){ throw new Error(res.error || "people_failed"); }
    el("profiles").innerHTML = (res.sources || []).map(
      s => `<a href="${s.url}" target="_blank" rel="noreferrer">${s.title || s.url}</a>`
    ).join("") || "لا توجد نتائج.";
  }catch(err){
    el("profiles").textContent = "حدث خطأ";
    console.error(err);
  }
}

document.getElementById("searchForm").addEventListener("submit", doSearch);
document.getElementById("peopleForm").addEventListener("submit", doPeople);
