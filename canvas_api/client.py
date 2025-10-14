import requests
from config import CANVAS_BASE_URL, CANVAS_TOKEN

class CanvasClient:
    def __init__(self, base_url=CANVAS_BASE_URL, token=CANVAS_TOKEN):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def get(self, endpoint, params=None):
        # Handle pagination for GET requests
        url = f"{self.base_url}/{endpoint}"
        all_results = []
        while url:
            response = requests.get(url, headers=self.headers, params=params)
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