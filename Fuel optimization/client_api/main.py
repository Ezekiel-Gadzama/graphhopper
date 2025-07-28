from fastapi import FastAPI
from .router import router

app = FastAPI(
    title="Client Routing API",
    description="Provides default and optimized routes with fuel savings info",
    version="1.0"
)

app.include_router(router, prefix="/api")
