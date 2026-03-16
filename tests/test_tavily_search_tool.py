"""Tests for Tavily Search tool."""

import httpx
import json
import pytest

from nanobot.agent.tools.web import TavilySearchTool
from nanobot.config.schema import TavilySearchConfig


def _tool(api_key: str = "", max_results: int = 5) -> TavilySearchTool:
    return TavilySearchTool(config=TavilySearchConfig(api_key=api_key, max_results=max_results))


def _response(status: int = 200, json: dict | None = None) -> httpx.Response:
    """Build a mock httpx.Response with a dummy request attached."""
    r = httpx.Response(status, json=json)
    r._request = httpx.Request("POST", "https://mock")
    return r


@pytest.mark.asyncio
async def test_tavily_search(monkeypatch):
    async def mock_post(self, url, **kw):
        assert "tavily" in url
        assert kw["headers"]["Authorization"] == "Bearer tavily-key"
        return _response(json={
            "results": [{"title": "OpenClaw", "url": "https://openclaw.io", "content": "Framework"}]
        })

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    tool = _tool(api_key="tavily-key")
    result = await tool.execute(query="openclaw")
    assert "OpenClaw" in result
    assert "https://openclaw.io" in result


@pytest.mark.asyncio
async def test_tavily_search_with_count(monkeypatch):
    async def mock_post(self, url, **kw):
        assert kw["json"]["max_results"] == 3
        return _response(json={
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "content": "Content 1"},
                {"title": "Result 2", "url": "https://example.com/2", "content": "Content 2"},
                {"title": "Result 3", "url": "https://example.com/3", "content": "Content 3"}
            ]
        })

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    tool = _tool(api_key="tavily-key")
    result = await tool.execute(query="test", count=3)
    assert "Result 1" in result
    assert "Result 2" in result
    assert "Result 3" in result


@pytest.mark.asyncio
async def test_tavily_search_no_api_key():
    tool = _tool(api_key="")
    result = await tool.execute(query="test")
    assert "Error" in result
    assert "API key not configured" in result


@pytest.mark.asyncio
async def test_tavily_search_no_results(monkeypatch):
    async def mock_post(self, url, **kw):
        return _response(json={"results": []})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    tool = _tool(api_key="tavily-key")
    result = await tool.execute(query="test")
    assert "No results" in result


@pytest.mark.asyncio
async def test_tavily_search_http_error_401(monkeypatch):
    async def mock_post(self, url, **kw):
        return _response(status=401, json={"error": "Invalid API key"})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    tool = _tool(api_key="tavily-key")
    result = await tool.execute(query="test")
    assert "Error" in result
    assert "Invalid Tavily API key" in result


@pytest.mark.asyncio
async def test_tavily_search_http_error_429(monkeypatch):
    async def mock_post(self, url, **kw):
        return _response(status=429, json={"error": "Rate limit exceeded"})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    tool = _tool(api_key="tavily-key")
    result = await tool.execute(query="test")
    assert "Error" in result
    assert "Rate limit exceeded" in result


@pytest.mark.asyncio
async def test_tavily_search_http_error_other(monkeypatch):
    async def mock_post(self, url, **kw):
        return _response(status=500, json={"error": "Internal server error"})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    tool = _tool(api_key="tavily-key")
    result = await tool.execute(query="test")
    assert "HTTP error" in result
    assert "500" in result


@pytest.mark.asyncio
async def test_tavily_search_request_error(monkeypatch):
    async def mock_post(self, url, **kw):
        raise httpx.RequestError("Connection error")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    tool = _tool(api_key="tavily-key")
    result = await tool.execute(query="test")
    assert "Request error" in result
    assert "Connection error" in result


@pytest.mark.asyncio
async def test_tavily_search_json_decode_error(monkeypatch):
    async def mock_post(self, url, **kw):
        r = _response(status=200, json=None)
        # Override json method to raise decode error
        def mock_json():
            raise json.JSONDecodeError("Invalid JSON", "", 0)
        r.json = mock_json
        return r

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    tool = _tool(api_key="tavily-key")
    result = await tool.execute(query="test")
    assert "Error" in result
    assert "Invalid response from Tavily API" in result


@pytest.mark.asyncio
async def test_tavily_search_generic_error(monkeypatch):
    async def mock_post(self, url, **kw):
        raise Exception("Generic error")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    tool = _tool(api_key="tavily-key")
    result = await tool.execute(query="test")
    assert "Error" in result
    assert "Generic error" in result
