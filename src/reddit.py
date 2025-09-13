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
        query = f"Use the following context to answer the question below in detail. " \
                f"If the context is irrelevant, do not answer the query.\n\n{query}"
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(f"{os.getenv('ASK_PESU_URL')}/ask", json={"query": query})
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            logging.exception(f"Failed to query AskPESU API for post {post.id}")
            return {"status": False}
