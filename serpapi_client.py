"""
serpapi_client.py
------------------
Thin wrapper around SerpApi's Google Shopping engine.

Docs: https://serpapi.com/google-shopping-api
Also uses Google Shopping Product API (product_id lookup) to pull a
per-seller price breakdown, which enables multi-seller comparison
(comparing prices across stores like Amazon, Flipkart, Croma, etc.).
"""

import os
import time
from typing import Dict, List, Optional, Any

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SERPAPI_BASE_URL = "https://serpapi.com/search.json"


class SerpApiError(Exception):
    """Raised when SerpApi returns an error or an unexpected payload."""


class SerpApiClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 45):
        self.api_key = api_key or os.environ.get("SERPAPI_API_KEY")
        if not self.api_key:
            raise SerpApiError(
                "No SerpApi key found. Set SERPAPI_API_KEY as an env var "
                "or pass api_key= explicitly. Get a free key (250 "
                "searches/month) at https://serpapi.com/users/sign_up"
            )
        self.timeout = timeout

    def _get(self, params: dict, retries: int = 1, backoff: float = 1.0) -> dict:
        params = {**params, "api_key": self.api_key}
        last_err = None
        for attempt in range(retries + 1):
            try:
                resp = requests.get(SERPAPI_BASE_URL, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if data.get("error"):
                    raise SerpApiError(data["error"])
                return data
            except (requests.RequestException, SerpApiError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(backoff * (attempt + 1))
                continue
        raise SerpApiError(f"SerpApi request failed after {retries + 1} attempts: {last_err}")

    def search_shopping(self, query: str, location: Optional[str] = None, gl: str = "in", hl: str = "en") -> List[Dict[str, Any]]:
        """
        Search Google Shopping for a query and return a normalized list of listings:
        {title, source, price, extracted_price, product_id, product_link, thumbnail, rating, reviews}.
        """
        params = {
            "engine": "google_shopping",
            "q": query,
            "gl": gl,
            "hl": hl,
        }
        if location:
            params["location"] = location

        data = self._get(params)
        results = data.get("shopping_results", [])
        normalized = []
        for r in results:
            normalized.append({
                "title": r.get("title"),
                "source": r.get("source"),
                "price": r.get("price"),
                "extracted_price": r.get("extracted_price"),
                "product_id": r.get("product_id"),
                "product_link": r.get("product_link") or r.get("link"),
                "thumbnail": r.get("thumbnail"),
                "rating": r.get("rating"),
                "reviews": r.get("reviews"),
            })
        return normalized

    def get_product_sellers(self, product_id: str, gl: str = "in") -> List[Dict[str, Any]]:
        """
        Given a Google Shopping product_id, fetch the seller/price breakdown
        via the google_product engine's sellers results. This allows comparing
        prices across sellers (Amazon, Flipkart, Croma, Reliance Digital, etc.).
        """
        if not product_id:
            return []
        params = {
            "engine": "google_product",
            "product_id": product_id,
            "gl": gl,
            "offers": "true",
        }
        try:
            data = self._get(params)
        except SerpApiError:
            return []

        sellers = data.get("sellers_results", {}).get("online_sellers", [])
        normalized = []
        for s in sellers:
            price_val = s.get("extracted_price") or s.get("extracted_base_price") or s.get("extracted_total_price")
            raw_price = s.get("price") or s.get("base_price") or s.get("total_price")
            normalized.append({
                "name": s.get("name") or s.get("seller"),
                "price": raw_price,
                "extracted_price": price_val,
                "link": s.get("link") or s.get("direct_link"),
                "details": s.get("details"),
            })
        return normalized
