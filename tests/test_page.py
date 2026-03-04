from scraper.page import PageData, Section, _extract_review_dates, _find_tab_urls, parse_page
from bs4 import BeautifulSoup


def test_parse_single_page(single_page_html):
    content, last_reviewed, next_review = parse_page(single_page_html, "https://www.nhs.uk/conditions/acne/")
    assert "Acne" in content
    assert "common skin condition" in content
    assert last_reviewed == "03 January 2023"
    assert next_review == "03 January 2026"


def test_extract_review_dates(single_page_html):
    soup = BeautifulSoup(single_page_html, "html.parser")
    last, next_ = _extract_review_dates(soup)
    assert last == "03 January 2023"
    assert next_ == "03 January 2026"


def test_extract_review_dates_missing():
    soup = BeautifulSoup("<html><body><p>No dates here</p></body></html>", "html.parser")
    last, next_ = _extract_review_dates(soup)
    assert last == ""
    assert next_ == ""


def test_find_tab_urls(tabbed_page_html):
    soup = BeautifulSoup(tabbed_page_html, "html.parser")
    tabs = _find_tab_urls(soup, "https://www.nhs.uk/conditions/acne/")
    assert len(tabs) == 2
    assert tabs[0] == ("Overview", "https://www.nhs.uk/conditions/acne/")
    assert tabs[1] == ("Causes", "https://www.nhs.uk/conditions/acne/causes/")


def test_find_tab_urls_no_tabs(single_page_html):
    soup = BeautifulSoup(single_page_html, "html.parser")
    tabs = _find_tab_urls(soup, "https://www.nhs.uk/conditions/acne/")
    assert tabs == []
