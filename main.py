@app.get("/", response_class=HTMLResponse)
async def home():
    """الصفحة الرئيسية مع نموذج البحث ولوحة الرموز + رابط حل من صورة"""
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>🤖 بسام الذكي - BASSAM AI APP</title>
      <style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px;direction:rtl}
        .container{max-width:800px;margin:0 auto;background:#fff;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,.1);overflow:hidden}
        .header{background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);color:#fff;padding:40px 30px;text-align:center}
        .header h1{font-size:2.4em;margin-bottom:8px}
        .content{padding:28px}
        .form-group{margin-bottom:16px}
        label{display:block;margin-bottom:8px;font-weight:bold;color:#333}
        input[type="text"]{width:100%;padding:14px;border:2px solid #e1e5e9;border-radius:10px;font-size:16px}
        input[type="text"]:focus{border-color:#4facfe;outline:none}
        .mode-selector{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:14px 0}
        .mode-btn{padding:12px;border:2px solid #e1e5e9;background:#fff;border-radius:10px;cursor:pointer;text-align:center;font-weight:bold;display:flex;align-items:center;justify-content:center;gap:8px}
        .mode-btn.active{background:#4facfe;color:#fff;border-color:#4facfe}
        .submit-btn{width:100%;padding:16px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;border:none;border-radius:12px;font-size:18px;font-weight:bold;cursor:pointer}
        .hint{color:#555;font-size:12px;margin-top:6px}
        .math-keyboard{display:none;flex-wrap:wrap;gap:8px;margin:8px 0 14px 0}
        .math-keyboard button{border:1px solid #dbe1e7;background:#fff;border-radius:8px;padding:8px 10px;cursor:pointer;font-size:14px}
        .features{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:18px;margin-top:22px}
        .feature{background:#f8f9fa;padding:16px;border-radius:10px;text-align:center}
        .footer{background:#f8f9fa;padding:18px;text-align:center;color:#666;border-top:1px solid #eee}
        a.link{color:#4f46e5;text-decoration:none}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>🤖 بسام الذكي</h1>
          <p>مساعدك للبحث والرياضيات والذكاء الاصطناعي</p>
        </div>

        <div class="content">
          <p style="margin-bottom:10px">
            📷 تبي تحل من صورة؟ <a class="link" href="/upload">جرّب حل مسألة من صورة</a>
          </p>

          <form method="post" action="/search">
            <div class="form-group">
              <label for="query">اطرح سؤالك أو مسألتك:</label>
              <input id="query" name="query" type="text"
                     placeholder="مثال: حل 2*x**2 + 3*x - 2 = 0 | تكامل sin(x) من 0 إلى pi | اشتق 3*x**2 + 5*x - 7"
                     required>
              <div class="hint">تلميح: استخدم <code>x**2</code> للأسس، <code>sqrt(x)</code> للجذر، <code>pi</code> لِـπ.</div>
            </div>

            <div id="math-kbd" class="math-keyboard">
              <button type="button" onclick="ins('**')">^ برمجي ( ** )</button>
              <button type="button" onclick="ins('sqrt()')">√ الجذر</button>
              <button type="button" onclick="ins('pi')">π</button>
              <button type="button" onclick="ins('sin()')">sin</button>
              <button type="button" onclick="ins('cos()')">cos</button>
              <button type="button" onclick="ins('tan()')">tan</button>
              <button type="button" onclick="ins('ln()')">ln</button>
              <button type="button" onclick="templ('solve')">حل معادلة</button>
              <button type="button" onclick="templ('diff')">مشتقة</button>
              <button type="button" onclick="templ('int')">تكامل محدد</button>
            </div>

            <div class="mode-selector">
              <label class="mode-btn active"><input type="radio" name="mode" value="smart" checked style="display:none">🤖 ذكي</label>
              <label class="mode-btn"><input type="radio" name="mode" value="search" style="display:none">🔍 بحث</label>
              <label class="mode-btn"><input type="radio" name="mode" value="math" style="display:none">📊 رياضيات</label>
              <label class="mode-btn"><input type="radio" name="mode" value="images" style="display:none">🖼️ صور</label>
            </div>

            <button type="submit" class="submit-btn">🚀 ابدأ</button>
          </form>

          <div class="features">
            <div class="feature"><h3>🤖 ذكاء اصطناعي</h3><p>إجابات ذكية بالعربية</p></div>
            <div class="feature"><h3>📊 رياضيات</h3><p>مشتقات، تكاملات، حلول</p></div>
            <div class="feature"><h3>🔍 بحث</h3><p>بحث وتلخيص المحتوى</p></div>
            <div class="feature"><h3>🌐 دعم العربية</h3><p>مصمم للمستخدم العربي</p></div>
          </div>
        </div>

        <div class="footer">
          <p>تطبيق بسام الذكي - BASSAM AI APP</p>
        </div>
      </div>

      <script>
        // تبديل تفعيل أزرار الوضع
        document.querySelectorAll('.mode-btn').forEach(btn=>{
          btn.addEventListener('click', ()=>{
            document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active'));
            btn.classList.add('active');
            btn.querySelector('input').checked = true;
            toggleKbd();
          });
        });

        function ins(s){
          const el = document.getElementById('query');
          const st = el.selectionStart, en = el.selectionEnd;
          el.value = el.value.slice(0,st) + s + el.value.slice(en);
          el.focus(); const p = st + s.length; el.setSelectionRange(p,p);
        }
        function templ(k){
          const el = document.getElementById('query'); let t="";
          if(k==='solve') t="حل 2*x**2 + 3*x - 2 = 0";
          if(k==='diff')  t="اشتق 3*x**2 + 5*x - 7";
          if(k==='int')   t="تكامل sin(x) من 0 إلى pi";
          el.value = t; el.focus(); el.setSelectionRange(t.length,t.length);
        }
        function toggleKbd(){
          const mode = document.querySelector('input[name="mode"]:checked').value;
          document.getElementById('math-kbd').style.display = (mode==='math') ? 'flex' : 'none';
        }
        window.addEventListener('DOMContentLoaded', ()=>{ document.getElementById('query').focus(); toggleKbd(); });
      </script>
    </body>
    </html>
    """
