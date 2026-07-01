"""API module for the Deep Research Agent Platform."""

from .research import router as research_router
from .knowledge import router as knowledge_router
from .sql import router as sql_router

__all__ = ["research_router", "knowledge_router", "sql_router"]
