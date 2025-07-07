import os
os.environ.pop("SSL_CERT_FILE", None)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import calendar_routes

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def root():
    return {"message": "AI Agent Backend is Running"}
@app.get("/healthz")
def healthz():
    return {"status": "ok"}
app.include_router(calendar_routes.router)
