from fastapi import FastAPI

from repartos.routers import operario

app = FastAPI(title="SIGER — Sistema Integral de Gestión de Repartos")

# Cada router agrupa los endpoints de una interfaz.
app.include_router(operario.router)


@app.get("/")
def health():
    return {"status": "ok"}
