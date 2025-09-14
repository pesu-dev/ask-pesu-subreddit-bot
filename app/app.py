"""Main entry point of the r/PESU subreddit bot that replies to new posts on with answers generated from the AskPESU."""

import argparse
import datetime
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.reddit import RedditClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan event handler for startup and shutdown events."""
    # Startup
    logging.info("AskPESU Subreddit Bot API startup")
    logging.info("Starting background scheduler for subreddit bot...")

    # Load config
    with open("conf/config.yaml") as f:
        config = yaml.safe_load(f)

    n = config.get("n", 10)
    interval = config.get("interval", 10)

    # Initialize Reddit client
    client = RedditClient()

    # Set up background scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        client.run,
        "interval",
        minutes=interval,
        args=[interval, n],
        next_run_time=datetime.datetime.now(datetime.UTC),
    )
    scheduler.start()
    logging.info("Background scheduler started.")

    yield

    # Shutdown
    scheduler.shutdown()
    logging.info("Background scheduler stopped.")
    logging.info("AskPESU Subreddit Bot shutdown.")


app = FastAPI(
    title="AskPESU Subreddit Bot API",
    description="Backend APIs for AskPESU Subreddit Bot, a question-answering bot for r/PESU.",
    version="0.1.0",
    docs_url="/",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Monitoring",
            "description": "Health checks and other monitoring endpoints.",
        },
    ],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions."""
    logging.exception("Unhandled exception occurred.")
    return JSONResponse(
        status_code=500,
        content={
            "status": False,
            "message": "Internal Server Error. Please try again later.",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        },
    )


@app.get(
    "/health",
    response_class=JSONResponse,
    tags=["Monitoring"],
)
async def health() -> JSONResponse:
    """Health check endpoint."""
    logging.debug("Health check requested.")
    return JSONResponse(
        status_code=200,
        content={
            "status": True,
            "message": "ok",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        },
    )


if __name__ == "__main__":
    # load environment variables from .env file
    load_dotenv()

    # Set up argument parser for command line arguments
    parser = argparse.ArgumentParser(
        description="Run the FastAPI application for AskPESU Subreddit Bot API.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to run the FastAPI application on. Default is 0.0.0.0",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to run the FastAPI application on. Default is 7860",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run the application in debug mode with detailed logging.",
    )
    args = parser.parse_args()

    # Set up logging configuration
    logging_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s",
        filemode="w",
    )

    # Run the app
    uvicorn.run("app.app:app", host=args.host, port=args.port, reload=args.debug)
