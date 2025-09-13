"""Main entry point of the subreddit bot that replies to new posts with answers generated from the AskPESU API."""

import datetime
import logging

import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from reddit import RedditClient


def run(interval: int, n: int) -> None:
    """Main job function to fetch and process new posts.

    Args:
        interval (int): Time window in minutes to look back for new posts.
        n (int): Number of posts to fetch.

    Returns:
        None
    """
    # Fetch all the new posts in the last interval minutes
    new_posts = client.fetch_latest_posts(interval, n)
    logging.info(f"Fetched {len(new_posts)} new posts.")
    for post in new_posts:
        try:
            # Query the AskPESU API with the post's title and content
            response = client.query_ask_pesu(post)
            # Respond with an answer only if the response is valid and not the default fallback answer
            if (
                response["status"]
                and (answer := response.get("answer"))
                and answer != "I'm sorry, I don't have that information."
            ):
                answer = f"{answer}\n\n---\n*I am a bot, and this action was performed automatically.*"
                logging.debug(answer)
                post.reply(answer)
                logging.info(f"Replied to post: {post.id} - {post.title}")
        except Exception:
            logging.exception(f"Failed to process post: {post.id} - {post.title}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s : %(filename)s - %(funcName)s : %(message)s",
    )

    # load environment variables from .env file
    load_dotenv()

    # Load the config file
    with open("conf/config.yaml") as f:
        config = yaml.safe_load(f)

    # Load configuration parameters
    n = config.get("n", 5)  # number of posts to fetch every interval
    interval = config.get("interval", 10)  # time window in minutes to look back for new posts

    # Connect to Reddit API
    client = RedditClient()

    # Set up scheduler
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run,
        "interval",
        minutes=interval,
        next_run_time=datetime.datetime.now(datetime.UTC),
        args=[interval, n],
    )

    # Start the scheduler
    scheduler.start()
