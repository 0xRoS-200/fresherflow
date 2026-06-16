"""Entry point for CV Customizer application"""

from cv_customizer.main import app

if __name__ == "__main__":
    import uvicorn
    from cv_customizer.config import AppConfig
    
    uvicorn.run(
        app,
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        log_level=AppConfig.LOG_LEVEL.lower(),
        reload=AppConfig.DEBUG,
    )
