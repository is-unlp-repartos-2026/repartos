from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from repartos.routers import operario, repartidor, seguimiento

app = FastAPI(
    title="SIGER — Sistema Integral de Gestión de Repartos"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(operario.router)
app.include_router(repartidor.router)
app.include_router(seguimiento.router)

@app.get("/")
def health():
    return {"status": "ok"}
