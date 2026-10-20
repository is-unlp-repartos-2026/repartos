from fastapi import FastAPI

app = FastAPI(title="SIGER — Sistema Integral de Gestión de Repartos")


@app.get("/")
def health():
    return {"status": "ok"}
