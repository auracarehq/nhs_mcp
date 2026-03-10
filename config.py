"""Scraper configuration: rate limiting and HTTP client settings."""

MAX_CONCURRENT = 3
REQUEST_DELAY = 0.5  # seconds between requests

USER_AGENT = (
    "NHSConditionsScraper/0.1 "
    "(educational project; +https://github.com)"
)
