import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.routes.endpoints import api_router
from app.core.config import settings


# Define allowed origins directly
ALLOWED_ORIGINS = [
    "http://localhost:3000",
]


# def init_database():
#     Base.metadata.create_all(bind=engine)


# @asynccontextmanager
# async def lifespan(app: FastAPI):  # pylint: disable=unused-argument
#     # Startup tasks
#     logger.info("Initializing database and creating tables.")
#     init_database()
#     logger.info("Database initialized and tables created.")

#     try:
#         yield
#     finally:
#         # Shutdown tasks (no session management needed here)
#         # Dispose of the database engine
#         logger.info("Checking active threads during shutdown...")
#         for thread in threading.enumerate():
#             logger.info(f"Thread still running: {thread.name}")
#         engine.dispose()

#         logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    # Initialize Sentry
    # setup(settings)

    main_app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/",
        generate_unique_id_function=lambda router: f"{router.tags[0]}-{router.name}",
        # lifespan=lifespan,
    )

    # Add Sentry ASGI middleware
    # main_app.add_middleware(SentryAsgiMiddleware)

    # Set CORS middleware with direct origins
    main_app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )

    # Include the routers
    main_app.include_router(api_router, prefix=settings.API_V1_STR)

    # # Add global exception handler
    # @main_app.exception_handler(Exception)
    # async def global_exception_handler(request, exc):  # pylint: disable=unused-argument
    #     logger.error(f"Unhandled exception: {exc}", exc_info=True)
    #     return handle_exception(exc)

    return main_app


app_ = create_app()


# if __name__ == "__main__":
#     uvicorn.run(app_, host="localhost", port=6677, timeout_graceful_shutdown=5)
