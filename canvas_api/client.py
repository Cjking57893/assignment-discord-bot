import requests
from typing import Dict, Any, Optional, List, Union
from config import CANVAS_BASE_URL, CANVAS_TOKEN

# Pagination settings for Canvas API
DEFAULT_PER_PAGE = 100

class CanvasClient:
    def __init__(self, base_url: str = CANVAS_BASE_URL, token: str = CANVAS_TOKEN):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        # Handle pagination for GET requests
        url = f"{self.base_url}/{endpoint}"
        # Default per_page unless already provided
        if params is None:
            params = {"per_page": DEFAULT_PER_PAGE}
        elif "per_page" not in params:
            params = {**params, "per_page": DEFAULT_PER_PAGE}
        all_results = []
        while url:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                all_results.extend(data)
            else:
                # For non-list responses (single object), just return
                return data
            # Parse Link header for pagination
            link = response.headers.get('Link', '')
            next_url = None
            for part in link.split(','):
                if 'rel="next"' in part:
                    next_url = part[part.find('<')+1:part.find('>')]
            url = next_url
            params = None  # Only use params on first request
        return all_results