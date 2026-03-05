import os
import json
import requests
from mcp.server.fastmcp import FastMCP

# ------------------------------------------------------------------------------------------------
# MCP War News Bridge
# Secure proxy for TinyTruce agents to access the Situation Room API (RSS War News)
# ------------------------------------------------------------------------------------------------

mcp = FastMCP("WarNews")

# Configuration (Ngrok Tunnel from .env)
BASE_URL = os.getenv("BASE_URL")
HEADERS = {
    "X-Proxy-Secret": os.getenv("WAR_API_SECRET"),
    "Content-Type": "application/json"
}

@mcp.tool()
def get_breaking_alerts(min_severity: float = 4.5, min_perspectives: int = 2):
    """
    Retrieves high-signal "Breaking Clusters" where multiple sources agree on a major event.
    Use this for urgent situational awareness.
    """
    url = f"{BASE_URL}/api/alerts"
    params = {
        "min_perspectives": min_perspectives,
        "min_severity": min_severity
    }
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Intelligence Desk Offline: {str(e)}"}

@mcp.tool()
def search_theater_news(query: str = None, region: str = "Global", hours: int = 24):
    """
    Searches for the latest processed articles with severity and bias analysis.
    Regions: Middle East, Global, North Korea, Sahel, etc.
    """
    url = f"{BASE_URL}/"
    params = {
        "q": query,
        "region": region,
        "hours": hours
    }
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

@mcp.tool()
def get_global_pulse():
    """
    Returns hourly deltas and trending regions. Good for detecting sudden spikes in activity.
    """
    url = f"{BASE_URL}/api/trends"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Pulse check failed: {str(e)}"}

if __name__ == "__main__":
    mcp.run()
