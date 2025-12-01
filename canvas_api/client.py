"""Canvas API client for making authenticated requests."""

import requests
from typing import Dict, Any, Optional, List, Union
from config import CANVAS_BASE_URL, CANVAS_TOKEN
from constants import DEFAULT_PER_PAGE


class CanvasAPIError(Exception):
    """Custom exception for Canvas API errors."""
    pass


class CanvasClient:
    """Client for interacting with the Canvas LMS API."""
    
    def __init__(self, base_url: str = CANVAS_BASE_URL, token: str = CANVAS_TOKEN) -> None:
        """Initialize the Canvas API client."""
        if not base_url or not token:
            raise ValueError("Canvas API base URL and token are required")
        
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Make a GET request to Canvas API with automatic pagination."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Set default pagination
        if params is None:
            params = {"per_page": DEFAULT_PER_PAGE}
        elif "per_page" not in params:
            params = {**params, "per_page": DEFAULT_PER_PAGE}
        
        all_results: List[Dict[str, Any]] = []
        
        try:
            while url:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, list):
                    all_results.extend(data)
                else:
                    # For non-list responses (single object), return immediately
                    return data
                
                # Parse Link header for pagination
                link = response.headers.get('Link', '')
                next_url = None
                for part in link.split(','):
                    if 'rel="next"' in part:
                        next_url = part[part.find('<') + 1:part.find('>')]
                        break
                
                url = next_url
                params = None  # Only use params on first request
            
            return all_results
            
        except requests.exceptions.RequestException as e:
            raise CanvasAPIError(f"Canvas API request failed: {e}") from e