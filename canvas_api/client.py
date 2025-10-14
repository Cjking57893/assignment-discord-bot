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
        response = requests.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()