"""Module to interact with Reddit by fetching latest posts and posting replies."""

import datetime
import logging
import os
from typing import Any

import httpx
import praw
from praw.models import Submission


class RedditClient:
    """Client to interact with Reddit API."""

    def __init__(self) -> None:
        """Initialize the Reddit client."""
        self.reddit = praw.Reddit(
            client_id=os.getenv("CLIENT_ID"),
            client_secret=os.getenv("CLIENT_SECRET"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            user_agent="pesudevbot",
            request_timeout=30,
        )
        self.subreddit = self.reddit.subreddit("PESU")

    def fetch_latest_posts(self, interval: int, n: int) -> list[Submission]:
        """Fetch the latest n posts from the subreddit within the last interval minutes.

        Args:
            interval (int): Time window in minutes to look back for new posts.
            n (int): Number of posts to fetch.

        Returns:
            list[Submission]: List of new posts.
        """
        current_time = datetime.datetime.now(datetime.UTC)
        cutoff = current_time - datetime.timedelta(minutes=interval)
        logging.info(f"Checking for new posts made from {cutoff} to {current_time}")
        new_posts: list[Submission] = []
        for post in self.subreddit.new(limit=n):
            created_time = datetime.datetime.fromtimestamp(post.created_utc, tz=datetime.UTC)
            if created_time >= cutoff:
                logging.info(f"[NEW POST]: {post.title} ({created_time}) -> {post.url}")
                new_posts.append(post)
                if len(new_posts) >= n:
                    break

        return new_posts

    @staticmethod
    def query_ask_pesu(post: Submission) -> dict[str, Any]:
        """Send a post's title+content to the AskPESU API and return the response.

        Args:
            post (Submission): The Reddit post to query.

        Returns:
            dict[str, Any]: The JSON response from the AskPESU API.
        """
        query = f"{post.title}\n\n{post.selftext or ''}".strip()
        base_url = os.getenv("ASK_PESU_URL")
        try:
            with httpx.Client(timeout=120) as client:
                quota = client.get(f"{base_url}/quota").json()["quota"]
                # Prefer thinking model if available
                if quota["thinking"]["available"]:
                    ask_resp = client.post(f"{base_url}/ask", json={"query": query, "thinking": True})
                # Check if primary model is available
                elif quota["primary"]["available"]:
                    ask_resp = client.post(f"{base_url}/ask", json={"query": query, "thinking": False})
                else:
                    logging.warning(f"No models available to answer post {post.id}")
                    return {"status": False}

                ask_resp.raise_for_status()
                return ask_resp.json()

        except httpx.HTTPError:
            logging.exception(f"Failed to query AskPESU API for post {post.id}")
            return {"status": False}

    def run(self, interval: int, n: int) -> None:
        """Main job function to fetch and process new posts.

        Args:
            interval (int): Time window in minutes to look back for new posts.
            n (int): Number of posts to fetch.

        Returns:
            None
        """
        # Fetch all the new posts in the last interval minutes
        new_posts = self.fetch_latest_posts(interval, n)
        logging.info(f"Fetched {len(new_posts)} new posts.")
        for post in new_posts:
            try:
                # Query the AskPESU API with the post's title and content
                response = self.query_ask_pesu(post)
                # Respond with an answer only if the response is valid and not the default fallback answer
                if (
                    response["status"]
                    and (answer := response.get("answer"))
                    and answer != "I'm sorry, I don't have that information."
                ):
                    answer = f"{answer}\n\n---\n*I am a bot, and this action was performed automatically.*"
                    post.reply(answer)
                    logging.info(f"Replied to post: {post.id} - {post.title}: {answer}")
            except Exception:
                logging.exception(f"Failed to process post: {post.id} - {post.title}")
