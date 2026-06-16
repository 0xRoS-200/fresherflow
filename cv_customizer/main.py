"""Main FastAPI application for CV Customizer"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cv_customizer.config import AppConfig
from cv_customizer.routers import parser, job_search, cv_tailor, health

# Configure logging
logging.basicConfig(
    level=AppConfig.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CV Customizer API",
    description="Resume parsing, job matching, and CV tailoring system",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(parser.router, prefix="/api/parser", tags=["Parser Agent"])
app.include_router(job_search.router, prefix="/api/jobs", tags=["Job Search Agent"])
app.include_router(cv_tailor.router, prefix="/api/tailor", tags=["CV Tailor Agent"])


@app.on_event("startup")
async def startup_event():
    logger.info("CV Customizer API started")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("CV Customizer API shutdown")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "cv_customizer.main:app",
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        reload=AppConfig.DEBUG,
    )
