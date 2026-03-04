from __future__ import annotations

import pytest

# Sample NHS A-Z index HTML
INDEX_HTML = """
<html><body>
<main id="maincontent">
  <h2>A</h2>
  <ul>
    <li><a href="/conditions/acne/">Acne</a></li>
    <li><a href="/conditions/asthma/">Asthma</a></li>
  </ul>
  <a href="/#nhsuk-nav-a-z">Back to top</a>
  <h2>B</h2>
  <ul>
    <li><a href="/conditions/bronchitis/">Bronchitis</a></li>
  </ul>
</main>
</body></html>
"""

# Sample single-page detail HTML (no tabs)
SINGLE_PAGE_HTML = """
<html><body>
<main id="maincontent">
  <h1>Acne</h1>
  <p>Acne is a common skin condition.</p>
  <h2>Symptoms</h2>
  <p>Spots on the face, back and chest.</p>
</main>
<p>Page last reviewed: 03 January 2023
Next review due: 03 January 2026</p>
</body></html>
"""

# Sample multi-tab detail page HTML
TABBED_PAGE_HTML = """
<html><body>
<main id="maincontent">
  <div>
    <h2>Contents</h2>
    <ol>
      <li>Overview</li>
      <li><a href="/conditions/acne/causes/">Causes</a></li>
    </ol>
  </div>
  <h1>Overview - Acne</h1>
  <p>Acne is a common skin condition.</p>
</main>
<p>Page last reviewed: 03 January 2023
Next review due: 03 January 2026</p>
</body></html>
"""

TAB_CAUSES_HTML = """
<html><body>
<main id="maincontent">
  <div>
    <h2>Contents</h2>
    <ol>
      <li><a href="/conditions/acne/">Overview</a></li>
      <li>Causes</li>
    </ol>
  </div>
  <h1>Causes - Acne</h1>
  <p>Acne is caused by blocked hair follicles.</p>
</main>
<p>Page last reviewed: 03 January 2023
Next review due: 03 January 2026</p>
</body></html>
"""


@pytest.fixture
def index_html():
    return INDEX_HTML


@pytest.fixture
def single_page_html():
    return SINGLE_PAGE_HTML


@pytest.fixture
def tabbed_page_html():
    return TABBED_PAGE_HTML


@pytest.fixture
def tab_causes_html():
    return TAB_CAUSES_HTML


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    # Also patch the domain data dirs
    for domain_cfg in config.DOMAINS.values():
        domain_name = domain_cfg["data_dir"].name
        domain_cfg["data_dir"] = tmp_path / domain_name
    return tmp_path
