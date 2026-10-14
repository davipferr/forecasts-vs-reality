import httpx
import pytest

from pipeline import http


@pytest.fixture
def mock_client(tmp_path, monkeypatch):
    """Route the shared client through a mock transport; record every request."""
    seen: list[httpx.Request] = []
    responses: dict[str, list[httpx.Response]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        queue = responses.get(request.url.path)
        return queue.pop(0) if queue else httpx.Response(200, content=b"[]")

    monkeypatch.setattr(http, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(http, "_client", httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    return seen, responses


def test_requests_share_one_client(mock_client):
    seen, _ = mock_client
    client = http._get_client()
    assert http.fetch("https://example.test/a") == b"[]"
    assert http.fetch("https://example.test/b") == b"[]"
    assert http._get_client() is client
    assert [r.url.path for r in seen] == ["/a", "/b"]


def test_cache_hit_skips_network_and_cached_path_finds_it(mock_client):
    seen, _ = mock_client
    assert http.cached_path("https://example.test/c", {"x": 1}) is None
    http.fetch("https://example.test/c", params={"x": 1})
    http.fetch("https://example.test/c", params={"x": 1})
    assert len(seen) == 1
    assert http.cached_path("https://example.test/c", {"x": 1}).read_bytes() == b"[]"


def test_retries_transient_errors_but_not_client_errors(mock_client):
    seen, responses = mock_client
    responses["/flaky"] = [httpx.Response(503), httpx.Response(200, content=b"[1]")]
    assert http.fetch("https://example.test/flaky") == b"[1]"
    responses["/bad"] = [httpx.Response(400, text="bad filter")]
    with pytest.raises(RuntimeError, match="400"):
        http.fetch("https://example.test/bad")
    assert [r.url.path for r in seen].count("/bad") == 1


def test_spaces_are_sent_as_percent_20(mock_client):
    # Olinda answers 400 to "+"-encoded spaces.
    seen, _ = mock_client
    http.fetch("https://example.test/odata", params={"$filter": "Indicador eq 'IPCA'", "$select": "Data,Mediana"})
    assert "%20eq%20" in str(seen[0].url) and "+" not in str(seen[0].url)
    assert "%24select=Data,Mediana" in http.full_url("https://example.test/odata", {"$select": "Data,Mediana"})


def test_non_json_body_is_retried_and_never_cached(mock_client):
    # SGS sometimes answers 200 with an empty body or an HTML error page.
    seen, responses = mock_client
    responses["/sgs"] = [httpx.Response(200, content=b""), httpx.Response(200, text="<html>Requisição inválida!</html>"), httpx.Response(200, content=b"[1]")]
    assert http.fetch("https://example.test/sgs", max_age=None) == b"[1]"
    assert [r.url.path for r in seen].count("/sgs") == 3

    responses["/down"] = [httpx.Response(200, content=b"")] * 5
    with pytest.raises(RuntimeError, match="not json"):
        http.fetch("https://example.test/down")
    assert http.cached_path("https://example.test/down") is None


def test_invalid_cached_body_is_refetched(mock_client):
    seen, _ = mock_client
    http._cache_path("https://example.test/old", None).write_bytes(b"")
    assert http.fetch("https://example.test/old", max_age=None) == b"[]"
    assert len(seen) == 1


def test_other_formats_reject_html_error_pages(mock_client):
    # imf.org and treasury.gov answer bot walls as HTML; never cache one as a spreadsheet or CSV.
    seen, responses = mock_client
    page = httpx.Response(200, text="<HTML><HEAD><TITLE>Access Denied</TITLE></HEAD></HTML>")
    responses["/book.xlsx"] = [page, httpx.Response(200, content=b"PKrest")]
    assert http.fetch("https://example.test/book.xlsx", fmt="xlsx", max_age=None) == b"PKrest"
    assert http.cached_path("https://example.test/book.xlsx", fmt="xlsx").suffix == ".xlsx"

    responses["/rates.csv"] = [page] * 5
    with pytest.raises(RuntimeError, match="not csv"):
        http.fetch("https://example.test/rates.csv", fmt="csv")
    assert http.cached_path("https://example.test/rates.csv", fmt="csv") is None
    assert seen[-1].headers["accept"].startswith("text/csv")
