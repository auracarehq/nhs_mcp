from pathlib import Path

BASE_URL = "https://www.nhs.uk"
DATA_DIR = Path(__file__).parent / "data"

MAX_CONCURRENT = 3
REQUEST_DELAY = 0.5  # seconds between requests

USER_AGENT = (
    "NHSConditionsScraper/0.1 "
    "(educational project; +https://github.com)"
)

DOMAINS = {
    "conditions": {
        "index_url": f"{BASE_URL}/conditions/",
        "data_dir": DATA_DIR / "conditions",
    },
    "symptoms": {
        "index_url": f"{BASE_URL}/symptoms/",
        "data_dir": DATA_DIR / "symptoms",
    },
    "medicines": {
        "index_url": f"{BASE_URL}/medicines/",
        "data_dir": DATA_DIR / "medicines",
    },
    "treatments": {
        "index_url": f"{BASE_URL}/tests-and-treatments/",
        "data_dir": DATA_DIR / "treatments",
    },
}
