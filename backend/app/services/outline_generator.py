"""
Outline Auto-Generation Service

Generates story outlines from a seed premise using AI.
Supports both staged (level-by-level) and full generation modes.
"""

import json
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from app.services.llm_service import LLMService
from app.config import settings


class GenerationScope(str, Enum):
    QUICK = "quick"       # ~8-10 scenes, 3 beats each
    STANDARD = "standard" # ~15 scenes, 4 beats each
    DETAILED = "detailed" # ~25 scenes, 5 beats each


class GenerationMode(str, Enum):
    STAGED = "staged"  # Level by level with review
    FULL = "full"      # Everything at once


class GenerationLevel(str, Enum):
    ACTS = "acts"
    CHAPTERS = "chapters"
    SCENES = "scenes"
    BEATS = "beats"


# Scope configuration
SCOPE_CONFIG = {
    GenerationScope.QUICK: {
        "acts": 3,
        "chapters_per_act": 3,
        "scenes_per_chapter": 1,
        "beats_per_scene": 3,
        "description": "Quick outline: 3 acts, ~9 scenes, ~27 beats"
    },
    GenerationScope.STANDARD: {
        "acts": 3,
        "chapters_per_act": 5,
        "scenes_per_chapter": 1,
        "beats_per_scene": 4,
        "description": "Standard outline: 3 acts, ~15 scenes, ~60 beats"
    },
    GenerationScope.DETAILED: {
        "acts": 4,
        "chapters_per_act": 6,
        "scenes_per_chapter": 1,
        "beats_per_scene": 5,
        "description": "Detailed outline: 4 acts, ~24 scenes, ~120 beats"
    }
}

# Token estimates (rough averages based on typical outputs)
TOKEN_ESTIMATES = {
    "act": 150,           # Tokens per act description
    "chapter": 100,       # Tokens per chapter description
    "scene": 200,         # Tokens per scene (title + outline)
    "beat": 50,           # Tokens per beat
    "prompt_overhead": 500  # Base prompt tokens
}

# Model pricing (per 1M tokens) - approximate for Sonnet
MODEL_PRICING = {
    "input": 3.00,   # $3 per 1M input tokens
    "output": 15.00  # $15 per 1M output tokens
}


def estimate_generation_cost(scope: GenerationScope) -> dict:
    """
    Estimate the cost of generating an outline at the given scope.

    Returns dict with token counts and estimated cost.
    """
    config = SCOPE_CONFIG[scope]

    total_acts = config["acts"]
    total_chapters = total_acts * config["chapters_per_act"]
    total_scenes = total_chapters * config["scenes_per_chapter"]
    total_beats = total_scenes * config["beats_per_scene"]

    # Estimate output tokens
    output_tokens = (
        total_acts * TOKEN_ESTIMATES["act"] +
        total_chapters * TOKEN_ESTIMATES["chapter"] +
        total_scenes * TOKEN_ESTIMATES["scene"] +
        total_beats * TOKEN_ESTIMATES["beat"]
    )

    # Estimate input tokens (prompts grow as context builds)
    # Rough estimate: base prompt + growing context
    input_tokens = (
        TOKEN_ESTIMATES["prompt_overhead"] * 4 +  # 4 generation calls
        output_tokens * 0.5  # Context from previous generations
    )

    # Calculate cost
    input_cost = (input_tokens / 1_000_000) * MODEL_PRICING["input"]
    output_cost = (output_tokens / 1_000_000) * MODEL_PRICING["output"]
    total_cost = input_cost + output_cost

    return {
        "scope": scope.value,
        "description": config["description"],
        "estimates": {
            "acts": total_acts,
            "chapters": total_chapters,
            "scenes": total_scenes,
            "beats": total_beats
        },
        "tokens": {
            "input": int(input_tokens),
            "output": int(output_tokens),
            "total": int(input_tokens + output_tokens)
        },
        "cost": {
            "input": round(input_cost, 4),
            "output": round(output_cost, 4),
            "total": round(total_cost, 4),
            "formatted": f"${total_cost:.2f}"
        }
    }


# Generation prompts
SYSTEM_PROMPT = """You are a skilled story architect helping writers create compelling narrative outlines.

Your outlines should:
- Create clear dramatic structure with rising tension
- Establish strong character arcs
- Plant setups that pay off later
- Vary pacing between high-tension and breathing room
- Include specific, concrete story beats (not generic placeholders)

IMPORTANT: You are creating an OUTLINE, not prose. Be concise but specific.
Each element should give the writer clear direction without being prescriptive about exact wording.

Always respond with valid JSON matching the requested structure."""


def get_acts_prompt(seed: str, scope: GenerationScope, genre: str = None, characters: List[str] = None) -> str:
    """Generate prompt for creating act structure."""
    config = SCOPE_CONFIG[scope]

    character_context = ""
    if characters:
        character_context = f"\n\nExisting characters to incorporate:\n" + "\n".join(f"- {c}" for c in characters)

    genre_context = f"\nGenre: {genre}" if genre else ""

    return f"""Create a {config['acts']}-act structure for the following story premise.
{genre_context}

PREMISE:
{seed}
{character_context}

Generate exactly {config['acts']} acts. For each act, provide:
- A descriptive title
- A 2-3 sentence description of what happens in this act
- The key dramatic question or tension driving the act

Respond with JSON in this exact format:
{{
    "acts": [
        {{
            "title": "Act title",
            "description": "What happens in this act...",
            "dramatic_question": "The key tension or question..."
        }}
    ]
}}"""


def get_chapters_prompt(seed: str, acts: List[dict], act_index: int, scope: GenerationScope) -> str:
    """Generate prompt for creating chapters within an act."""
    config = SCOPE_CONFIG[scope]
    act = acts[act_index]

    acts_context = "\n".join(
        f"Act {i+1}: {a['title']} - {a['description']}"
        for i, a in enumerate(acts)
    )

    return f"""Create {config['chapters_per_act']} chapters for Act {act_index + 1} of this story.

STORY PREMISE:
{seed}

FULL ACT STRUCTURE:
{acts_context}

CURRENT ACT TO EXPAND:
Act {act_index + 1}: {act['title']}
{act['description']}
Dramatic question: {act['dramatic_question']}

Generate exactly {config['chapters_per_act']} chapters for this act. For each chapter, provide:
- A chapter title
- A 1-2 sentence description of what happens

Respond with JSON in this exact format:
{{
    "chapters": [
        {{
            "title": "Chapter title",
            "description": "What happens in this chapter..."
        }}
    ]
}}"""


def get_scenes_prompt(seed: str, act: dict, chapter: dict, scope: GenerationScope) -> str:
    """Generate prompt for creating scenes within a chapter."""
    config = SCOPE_CONFIG[scope]

    return f"""Create {config['scenes_per_chapter']} scene(s) for this chapter.

STORY PREMISE:
{seed}

CURRENT ACT:
{act['title']}: {act['description']}

CHAPTER TO EXPAND:
{chapter['title']}: {chapter['description']}

Generate exactly {config['scenes_per_chapter']} scene(s). For each scene, provide:
- A scene title
- A detailed outline (3-5 sentences) describing what happens
- The POV character (if applicable)
- The emotional tone

Respond with JSON in this exact format:
{{
    "scenes": [
        {{
            "title": "Scene title",
            "outline": "Detailed description of what happens...",
            "pov": "Character name or 'Third person omniscient'",
            "tone": "e.g., tense, melancholic, hopeful"
        }}
    ]
}}"""


def get_beats_prompt(seed: str, scene: dict, scope: GenerationScope) -> str:
    """Generate prompt for creating beats within a scene."""
    config = SCOPE_CONFIG[scope]

    return f"""Create {config['beats_per_scene']} story beats for this scene.

STORY PREMISE:
{seed}

SCENE:
Title: {scene['title']}
Outline: {scene['outline']}
POV: {scene.get('pov', 'Not specified')}
Tone: {scene.get('tone', 'Not specified')}

Generate exactly {config['beats_per_scene']} beats. Each beat should be:
- A specific moment or action (not vague)
- In chronological order
- Building toward the scene's purpose

Respond with JSON in this exact format:
{{
    "beats": [
        {{
            "text": "What happens in this beat...",
            "notes": "Optional writer notes or reminders"
        }}
    ]
}}"""


class OutlineGenerator:
    """Service for generating story outlines."""

    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()
        self.total_tokens_used = 0
        self.total_cost = 0.0

    async def generate_acts(
        self,
        seed: str,
        scope: GenerationScope,
        genre: str = None,
        characters: List[str] = None,
        model: str = None
    ) -> dict:
        """Generate act structure from seed."""
        prompt = get_acts_prompt(seed, scope, genre, characters)

        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            model=model or "anthropic/claude-sonnet-4",
            max_tokens=2000,
            temperature=0.7
        )

        # Track usage
        self._track_usage(response)

        # Parse JSON response
        try:
            result = json.loads(response["content"])
            return {"success": True, "acts": result["acts"]}
        except (json.JSONDecodeError, KeyError) as e:
            return {"success": False, "error": f"Failed to parse response: {e}", "raw": response["content"]}

    async def generate_chapters(
        self,
        seed: str,
        acts: List[dict],
        act_index: int,
        scope: GenerationScope,
        model: str = None
    ) -> dict:
        """Generate chapters for a specific act."""
        prompt = get_chapters_prompt(seed, acts, act_index, scope)

        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            model=model or "anthropic/claude-sonnet-4",
            max_tokens=2000,
            temperature=0.7
        )

        self._track_usage(response)

        try:
            result = json.loads(response["content"])
            return {"success": True, "chapters": result["chapters"], "act_index": act_index}
        except (json.JSONDecodeError, KeyError) as e:
            return {"success": False, "error": f"Failed to parse response: {e}", "raw": response["content"]}

    async def generate_scenes(
        self,
        seed: str,
        act: dict,
        chapter: dict,
        scope: GenerationScope,
        model: str = None
    ) -> dict:
        """Generate scenes for a specific chapter."""
        prompt = get_scenes_prompt(seed, act, chapter, scope)

        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            model=model or "anthropic/claude-sonnet-4",
            max_tokens=2000,
            temperature=0.7
        )

        self._track_usage(response)

        try:
            result = json.loads(response["content"])
            return {"success": True, "scenes": result["scenes"]}
        except (json.JSONDecodeError, KeyError) as e:
            return {"success": False, "error": f"Failed to parse response: {e}", "raw": response["content"]}

    async def generate_beats(
        self,
        seed: str,
        scene: dict,
        scope: GenerationScope,
        model: str = None
    ) -> dict:
        """Generate beats for a specific scene."""
        prompt = get_beats_prompt(seed, scene, scope)

        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            model=model or "anthropic/claude-sonnet-4",
            max_tokens=1000,
            temperature=0.7
        )

        self._track_usage(response)

        try:
            result = json.loads(response["content"])
            return {"success": True, "beats": result["beats"]}
        except (json.JSONDecodeError, KeyError) as e:
            return {"success": False, "error": f"Failed to parse response: {e}", "raw": response["content"]}

    async def generate_full_outline(
        self,
        seed: str,
        scope: GenerationScope,
        genre: str = None,
        characters: List[str] = None,
        budget_limit: float = None,
        model: str = None
    ) -> dict:
        """
        Generate a complete outline in one operation.

        Args:
            seed: Story premise
            scope: Generation scope (quick/standard/detailed)
            genre: Optional genre
            characters: Optional list of character names
            budget_limit: Optional max cost in dollars
            model: Optional model override

        Returns:
            Complete outline structure with acts, chapters, scenes, and beats
        """
        self.total_tokens_used = 0
        self.total_cost = 0.0

        outline = {
            "seed": seed,
            "scope": scope.value,
            "genre": genre,
            "acts": []
        }

        # Generate acts
        acts_result = await self.generate_acts(seed, scope, genre, characters, model)
        if not acts_result["success"]:
            return {"success": False, "error": acts_result["error"], "partial": outline}

        acts = acts_result["acts"]

        # Check budget
        if budget_limit and self.total_cost >= budget_limit:
            outline["acts"] = [{"title": a["title"], "description": a["description"], "chapters": []} for a in acts]
            return {
                "success": True,
                "partial": True,
                "stopped_at": "acts",
                "outline": outline,
                "usage": self._get_usage()
            }

        # Generate chapters for each act
        for act_idx, act in enumerate(acts):
            act_data = {
                "title": act["title"],
                "description": act["description"],
                "dramatic_question": act.get("dramatic_question", ""),
                "chapters": []
            }

            chapters_result = await self.generate_chapters(seed, acts, act_idx, scope, model)
            if not chapters_result["success"]:
                act_data["error"] = chapters_result["error"]
                outline["acts"].append(act_data)
                continue

            # Check budget
            if budget_limit and self.total_cost >= budget_limit:
                outline["acts"].append(act_data)
                return {
                    "success": True,
                    "partial": True,
                    "stopped_at": "chapters",
                    "outline": outline,
                    "usage": self._get_usage()
                }

            # Generate scenes for each chapter
            for chapter in chapters_result["chapters"]:
                chapter_data = {
                    "title": chapter["title"],
                    "description": chapter["description"],
                    "scenes": []
                }

                scenes_result = await self.generate_scenes(seed, act, chapter, scope, model)
                if not scenes_result["success"]:
                    chapter_data["error"] = scenes_result["error"]
                    act_data["chapters"].append(chapter_data)
                    continue

                # Check budget
                if budget_limit and self.total_cost >= budget_limit:
                    act_data["chapters"].append(chapter_data)
                    outline["acts"].append(act_data)
                    return {
                        "success": True,
                        "partial": True,
                        "stopped_at": "scenes",
                        "outline": outline,
                        "usage": self._get_usage()
                    }

                # Generate beats for each scene
                for scene in scenes_result["scenes"]:
                    scene_data = {
                        "title": scene["title"],
                        "outline": scene["outline"],
                        "pov": scene.get("pov"),
                        "tone": scene.get("tone"),
                        "beats": []
                    }

                    beats_result = await self.generate_beats(seed, scene, scope, model)
                    if beats_result["success"]:
                        scene_data["beats"] = beats_result["beats"]
                    else:
                        scene_data["error"] = beats_result["error"]

                    chapter_data["scenes"].append(scene_data)

                    # Check budget after each scene's beats
                    if budget_limit and self.total_cost >= budget_limit:
                        act_data["chapters"].append(chapter_data)
                        outline["acts"].append(act_data)
                        return {
                            "success": True,
                            "partial": True,
                            "stopped_at": "beats",
                            "outline": outline,
                            "usage": self._get_usage()
                        }

                act_data["chapters"].append(chapter_data)

            outline["acts"].append(act_data)

        return {
            "success": True,
            "partial": False,
            "outline": outline,
            "usage": self._get_usage()
        }

    def _track_usage(self, response: dict):
        """Track token usage and cost from a response."""
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        self.total_tokens_used += input_tokens + output_tokens

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * MODEL_PRICING["input"]
        output_cost = (output_tokens / 1_000_000) * MODEL_PRICING["output"]
        self.total_cost += input_cost + output_cost

    def _get_usage(self) -> dict:
        """Get current usage stats."""
        return {
            "total_tokens": self.total_tokens_used,
            "total_cost": round(self.total_cost, 4),
            "cost_formatted": f"${self.total_cost:.2f}"
        }
