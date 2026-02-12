"""Persona MCP client — talks to the Persona MCP server for identity, memory, and emotional state.

Used by chico_service for chat and (later) by generation_service for pre-gen/post-canon hooks.
All methods are non-fatal: they return None/empty on failure so callers can fall back gracefully.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport

from app.config import settings

logger = logging.getLogger("app.services.persona_client")


class PersonaClient:
    """HTTP client for Persona MCP server."""

    def __init__(self, url: str):
        self.url = url
        self._healthy: bool = False
        self._last_check: float = 0
        self._cache_ttl: float = 30  # seconds between health checks

    async def _call_tool(self, tool_name: str, args: dict, timeout: float = 30) -> dict | list:
        """Call a Persona MCP tool and return parsed result.

        Uses FastMCP client with fallback to raw HTTP for structured_content bug.
        Raises on error — callers should wrap in try/except.
        """
        transport = StreamableHttpTransport(url=self.url)
        async with Client(transport=transport, timeout=timeout) as client:
            try:
                result = await client.call_tool(tool_name, args)
            except Exception as e:
                if "structured_content must be a dict" in str(e):
                    return await self._raw_call(tool_name, args, timeout)
                raise

            if result.is_error:
                error_text = ""
                for block in result.content:
                    if hasattr(block, "text"):
                        error_text += block.text
                raise RuntimeError(f"Persona MCP {tool_name}: {error_text}")

            text = ""
            for block in result.content:
                if hasattr(block, "text"):
                    text += block.text

            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}

    async def _raw_call(self, tool_name: str, args: dict, timeout: float = 30) -> dict | list:
        """Direct HTTP fallback for when FastMCP client chokes on structured_content."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
        }
        async with httpx.AsyncClient(timeout=timeout) as http:
            resp = await http.post(self.url, json=payload, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            raise RuntimeError(f"Persona MCP {tool_name}: {data['error']}")

        result = data.get("result", {})
        sc = result.get("structuredContent") or result.get("structured_content")
        if sc is not None:
            return sc

        content = result.get("content", [])
        text = ""
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")

        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {"text": text}

    # -------------------------------------------------------------------------
    # Public methods — all return None/empty on failure
    # -------------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Check if Persona MCP is reachable. Cached for 30s."""
        now = time.monotonic()
        if now - self._last_check < self._cache_ttl:
            return self._healthy

        try:
            await self._call_tool("persona_list", {})
            self._healthy = True
        except Exception as e:
            logger.warning(f"Persona MCP health check failed: {e}")
            self._healthy = False
        self._last_check = now
        return self._healthy

    async def list_personas(self) -> List[Dict[str, Any]]:
        """List all available personas. Returns empty list on failure."""
        try:
            result = await self._call_tool("persona_list", {})
            personas = result if isinstance(result, list) else result.get("personas", [])
            # Normalize: ensure each persona has 'id' and 'name' fields
            for p in personas:
                if "id" not in p:
                    p["id"] = p.get("persona_id", "")
                if "name" not in p:
                    p["name"] = p.get("display_name", p.get("persona_id", ""))
            return personas
        except Exception as e:
            logger.warning(f"Failed to list personas: {e}")
            return []

    async def get_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get a persona definition (name, role, etc.). Returns None on failure."""
        try:
            result = await self._call_tool("persona_get_state", {"persona_id": persona_id})
            if result:
                # Normalize field names
                if "name" not in result:
                    result["name"] = result.get("display_name", persona_id)
                if "personality" not in result:
                    result["personality"] = result.get("role", "")
            return result
        except Exception as e:
            logger.warning(f"Failed to get persona {persona_id}: {e}")
            return None

    async def get_context(
        self,
        persona_id: str,
        recent_count: int = 3,
        summary_count: int = 7,
    ) -> Optional[Dict[str, Any]]:
        """Get persona context: recent experiences, summaries, voice info.

        Returns None on failure.
        """
        try:
            return await self._call_tool("persona_get_context", {
                "persona_id": persona_id,
                "recent_count": recent_count,
                "summary_count": summary_count,
            })
        except Exception as e:
            logger.warning(f"Failed to get context for {persona_id}: {e}")
            return None

    async def get_emotional_arc(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get emotional arc: trend + recent emotional states. Returns None on failure."""
        try:
            return await self._call_tool("memory_get_emotional_arc", {"persona_id": persona_id})
        except Exception as e:
            logger.warning(f"Failed to get emotional arc for {persona_id}: {e}")
            return None

    async def get_callbacks(self, persona_id: str, limit: int = 5) -> List[str]:
        """Get memorable moments worth referencing. Returns empty list on failure."""
        try:
            result = await self._call_tool("memory_get_callbacks", {
                "persona_id": persona_id,
                "limit": limit,
            })
            callbacks = result.get("callbacks", [])
            return [c.get("text", c.get("content", "")) for c in callbacks if c]
        except Exception as e:
            logger.warning(f"Failed to get callbacks for {persona_id}: {e}")
            return []

    async def submit_experience(
        self,
        persona_id: str,
        content: str,
        emotional_state: str = "neutral",
        experience_type: str = "chat",
        key_insight: str = "",
    ) -> bool:
        """Submit an experience to a persona. Returns True on success, False on failure."""
        try:
            args: Dict[str, Any] = {
                "persona_id": persona_id,
                "source_app": "prose-pipeline",
                "experience_type": experience_type,
                "content": content,
                "emotional_state": emotional_state,
            }
            if key_insight:
                args["key_insight"] = key_insight
            await self._call_tool("persona_submit_experience", args)
            return True
        except Exception as e:
            logger.warning(f"Failed to submit experience for {persona_id}: {e}")
            return False

    async def get_full_context(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get combined persona context: base context + emotional arc + callbacks.

        Convenience method that aggregates multiple calls. Returns None if base context fails.
        """
        context = await self.get_context(persona_id)
        if context is None:
            return None

        # Enrich with emotional arc
        arc = await self.get_emotional_arc(persona_id)
        if arc:
            context["emotional_trend"] = arc.get("trend", "")
            states = arc.get("states", [])
            context["recent_emotions"] = [
                s.get("emotional_state", "") for s in states[-3:]
            ]

        # Enrich with callbacks
        context["callbacks"] = await self.get_callbacks(persona_id)

        return context


# Singleton instance
_persona_client: Optional[PersonaClient] = None


def get_persona_client() -> PersonaClient:
    """Get the singleton PersonaClient instance."""
    global _persona_client
    if _persona_client is None:
        _persona_client = PersonaClient(url=settings.persona_mcp_url)
    return _persona_client
