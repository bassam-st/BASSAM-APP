from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse

app = FastAPI()

html_form = """
<!DOCTYPE html>
<html>
    <head>
        <title>بسام الذكي</title>
    </head>
    <body style="font-family: Arial; text-align:center; margin-top:50px;">
        <h1>مرحباً بك في بسام الذكي 🤖</h1>
        <form method="post">
            <input type="text" name="question" placeholder="اكتب سؤالك هنا..." style="width:300px; padding:10px;">
            <button type="submit" style="padding:10px;">إرسال</button>
        </form>
        <h2>{answer}</h2>
    </body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def form_get():
    return html_form.format(answer="")

@app.post("/", response_class=HTMLResponse)
async def form_post(question: str = Form(...)):
    # هنا ممكن نضيف ذكاء اصطناعي يجاوب
    answer = f"سؤالك كان: {question} (الرد سيضاف لاحقاً 🤖)"
    return html_form.format(answer=answer)