"""Canvas API client package for interacting with the Canvas LMS API."""

from .client import CanvasClient
from .endpoints import get_courses, get_assignments

__all__ = ['CanvasClient', 'get_courses', 'get_assignments']
