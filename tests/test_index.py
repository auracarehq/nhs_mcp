from scraper.index import parse_index


def test_parse_index(index_html):
    entries = parse_index(index_html)
    assert len(entries) == 3
    assert entries[0].name == "Acne"
    assert entries[0].slug == "acne"
    assert entries[0].url == "https://www.nhs.uk/conditions/acne/"
    assert entries[1].slug == "asthma"
    assert entries[2].slug == "bronchitis"


def test_parse_index_empty():
    html = "<html><body><main></main></body></html>"
    entries = parse_index(html)
    assert entries == []


def test_parse_index_skips_duplicates():
    html = """
    <html><body><main>
    <a href="/conditions/acne/">Acne</a>
    <a href="/conditions/acne/">Acne (duplicate)</a>
    </main></body></html>
    """
    entries = parse_index(html)
    assert len(entries) == 1


def test_parse_index_skips_anchors():
    html = """
    <html><body><main>
    <a href="/#top">Back to top</a>
    <a href="/conditions/acne/">Acne</a>
    </main></body></html>
    """
    entries = parse_index(html)
    assert len(entries) == 1
    assert entries[0].slug == "acne"
