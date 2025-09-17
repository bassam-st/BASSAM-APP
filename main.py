from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "مرحبًا بك في تطبيق بسام الذكي على Replit!"}

@app.get("/hello/{name}")
def say_hello(name: str):
    return {"message": f"أهلاً {name}, التطبيق يعمل بنجاح 🚀"}