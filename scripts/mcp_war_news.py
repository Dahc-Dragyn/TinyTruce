import os
import json
import time
import requests
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# ------------------------------------------------------------------------------------------------
# MCP War News Bridge
# Secure proxy for TinyTruce agents to access the Situation Room API (RSS War News)
# ------------------------------------------------------------------------------------------------

mcp = FastMCP("WarNews")

# Configuration (Ngrok Tunnel from .env)
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
HEADERS = {
    "X-Proxy-Secret": os.getenv("WAR_API_SECRET"),
    "Content-Type": "application/json"
}

# Simple TTL Cache (600 seconds = 10 minutes)
_CACHE = {}
_CACHE_TTL = 600

def _get_cached_or_fetch(url: str, params: dict = None):
    # Create a unique, deterministic cache key
    cache_key = url + "?" + json.dumps(params, sort_keys=True) if params else url
    
    now = time.time()
    if cache_key in _CACHE:
        cached_data, timestamp = _CACHE[cache_key]
        if now - timestamp < _CACHE_TTL:
            print(f"[CACHE HIT] Serving from memory: {url}")
            return cached_data
            
    print(f"[CACHE MISS] Fetching fresh data: {url}")
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        _CACHE[cache_key] = (data, now)
        
        # Periodic cleanup of old keys (lazy eviction)
        keys_to_delete = [k for k, v in _CACHE.items() if now - v[1] >= _CACHE_TTL]
        for k in keys_to_delete:
            del _CACHE[k]
            
        return data
    except Exception as e:
        # Don't cache errors, just return them
        return {"error": f"Intelligence Desk Error: {str(e)}"}

@mcp.tool()
def get_breaking_alerts(min_severity: float = 4.5, min_perspectives: int = 2):
    """
    Retrieves high-signal "Breaking Clusters" where multiple sources agree on a major event.
    Use this for urgent situational awareness.
    """
    url = f"{BASE_URL}/war/api/alerts"
    params = {
        "min_perspectives": min_perspectives,
        "min_severity": min_severity
    }
    return _get_cached_or_fetch(url, params)

@mcp.tool()
def search_theater_news(query: str = None, region: str = "Global", hours: int = 24):
    """
    Searches for the latest processed articles with severity and bias analysis.
    Regions: Middle East, Global, North Korea, Sahel, etc.
    """
    url = f"{BASE_URL}/war/"
    params = {
        "q": query,
        "region": region,
        "hours": hours
    }
    return _get_cached_or_fetch(url, params)

@mcp.tool()
def get_global_pulse():
    """
    Returns hourly deltas and trending regions. Good for detecting sudden spikes in activity.
    """
    url = f"{BASE_URL}/war/api/trends"
    return _get_cached_or_fetch(url)

@mcp.tool()
def get_source_transparency():
    """
    Returns detailed transparency data on all news sources including bias and trust ratings.
    """
    url = f"{BASE_URL}/war/api/sources"
    return _get_cached_or_fetch(url)

if __name__ == "__main__":
    mcp.run()
