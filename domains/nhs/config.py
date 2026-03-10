"""NHS-specific configuration: base URL and domain registry."""

BASE_URL = "https://www.nhs.uk"

DOMAINS = {
    "conditions": {
        "index_url": f"{BASE_URL}/conditions/",
    },
    "symptoms": {
        "index_url": f"{BASE_URL}/symptoms/",
    },
    "medicines": {
        "index_url": f"{BASE_URL}/medicines/",
    },
    "treatments": {
        "index_url": f"{BASE_URL}/tests-and-treatments/",
    },
}
