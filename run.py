"""Run API Service."""

import contextlib
import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from core.settings import get_settings
from core.auth import AuthMiddleware


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    """Application lifespan handler."""
    yield


def create_app() -> fastapi.FastAPI:
    """Create FastAPI application."""
    settings = get_settings()

    app = fastapi.FastAPI(
        title="PartnerUp Backend",
        version="0.4.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add auth middleware
    app.add_middleware(AuthMiddleware)

    # Heartbeat endpoint
    @app.get("/heartbeat")
    def heartbeat():
        return {"status": "ok"}

    # Import and include routers
    from main.routes import router as main_router
    from communication.routes import router as communication_router
    from account.routes import router as account_router

    app.include_router(main_router, tags=["main"])
    app.include_router(communication_router, prefix="/com", tags=["communication"])
    app.include_router(account_router, prefix="/account", tags=["account"])

    return app


app = create_app()


if __name__ == "__main__":
    print(R"""

        |     |     =     |————\    |—————\   |—————     =     |\     /|
        |     |   =   =   |    —\   |     |   |        =   =   | \   / |
        |—————|  = = = =  |     —|  |—————/   |—————  = = = =  |  \ /  |
        |     |  =     =  |    —/   |    |    |       =     =  |   |   |
        |     |  =     =  |————/    |     \   |—————  =     =  |       |


                    #######################################
                            Anana-Backend-Main
                        --Powered by FastAPI--
        
                    2025(c) all copyrights reserved
                    #######################################


    [LOG OUTPUT]:
    """)

    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.http.host,
        port=settings.http.port,
    )
