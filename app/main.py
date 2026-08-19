from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import bootstrap_seed_users
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.routers import auth, documents, upload, versions


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_seed_users(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Docs App API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(upload.router)
app.include_router(versions.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
