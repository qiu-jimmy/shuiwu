from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable)


def compatible_tool(func: F) -> F:
    """Use LangChain's @tool when installed; otherwise keep a callable for mock mode."""
    try:
        from langchain.tools import tool

        return tool(func)  # type: ignore[return-value]
    except Exception:
        return func
