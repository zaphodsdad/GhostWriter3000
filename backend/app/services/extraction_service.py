"""Service for extracting characters, world, and style from manuscripts."""

import json
import re
from typing import Dict, Any, List, Optional
from app.services.llm_service import get_llm_service
from app.utils.prompt_templates import extract_json


class ExtractionService:
    """Service for AI-powered extraction of story elements from prose."""

    def __init__(self):
        self.llm = get_llm_service()

    async def extract_characters(
        self,
        text: str,
        model: Optional[str] = None,
        existing_characters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract character information from prose text.

        Args:
            text: Prose text to analyze
            model: Optional model override
            existing_characters: Names of already-known characters to skip

        Returns:
            Dict with 'characters' list and 'usage' stats
        """
        existing_list = ""
        if existing_characters:
            existing_list = f"\n\nAlready known characters (do not include these): {', '.join(existing_characters)}"

        system_prompt = """You are a literary analyst specializing in character extraction.
Analyze the provided prose and extract detailed character information.
Output valid JSON only, no markdown formatting or explanation."""

        user_prompt = f"""Analyze this prose and extract all characters mentioned. For each character, provide:
- name: Full name as it appears
- role: protagonist, antagonist, supporting, minor, or mentioned
- physical_description: Any physical details mentioned
- personality_traits: List of personality traits shown or implied
- relationships: Dict of relationships to other characters
- first_appearance: Brief context of how they first appear
- voice_patterns: Any distinctive speech patterns or verbal tics
- notes: Any other relevant details
{existing_list}

Output as JSON array:
[
  {{
    "name": "Character Name",
    "role": "supporting",
    "physical_description": "tall, dark hair",
    "personality_traits": ["brave", "impulsive"],
    "relationships": {{"Other Character": "sibling"}},
    "first_appearance": "Enters the tavern in chapter 1",
    "voice_patterns": "Uses military jargon",
    "notes": "Seems to have a hidden agenda"
  }}
]

PROSE TO ANALYZE:
{text[:50000]}"""  # Limit to ~50k chars to stay within context

        result = await self.llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=4000,
            temperature=0.3
        )

        # Parse the JSON response
        try:
            characters = extract_json(result["content"])
            if not isinstance(characters, list):
                characters = [characters] if characters else []
        except (json.JSONDecodeError, ValueError):
            # Try to extract JSON from the response
            characters = self._extract_json_from_text(result["content"])

        return {
            "characters": characters,
            "usage": result["usage"]
        }

    async def extract_world(
        self,
        text: str,
        model: Optional[str] = None,
        existing_elements: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract world-building elements from prose text.

        Args:
            text: Prose text to analyze
            model: Optional model override
            existing_elements: Names of already-known world elements to skip

        Returns:
            Dict with 'world_elements' list and 'usage' stats
        """
        existing_list = ""
        if existing_elements:
            existing_list = f"\n\nAlready known elements (do not duplicate): {', '.join(existing_elements)}"

        system_prompt = """You are a world-building analyst specializing in extracting lore and setting details.
Analyze the provided prose and extract world-building information.
Output valid JSON only, no markdown formatting or explanation."""

        user_prompt = f"""Analyze this prose and extract all world-building elements. Categorize them as:

1. LOCATIONS: Places, regions, buildings
2. MAGIC_SYSTEMS: Any supernatural abilities, rules, or limitations
3. TECHNOLOGY: Tools, weapons, transportation, tech level
4. HISTORY: Historical events, legends, past conflicts
5. POLITICS: Governments, factions, power structures
6. CULTURE: Customs, religions, social norms
7. CREATURES: Non-human beings, monsters, species
8. ITEMS: Important objects, artifacts, resources
{existing_list}

For each element provide:
- name: Element name
- category: One of the categories above
- description: Detailed description from the text
- rules: Any rules or constraints mentioned (especially for magic/tech)
- connections: Related elements or characters
- notes: Additional observations

Output as JSON array:
[
  {{
    "name": "The Shattered Empire",
    "category": "POLITICS",
    "description": "A fallen empire that once ruled the continent",
    "rules": null,
    "connections": ["Emperor Valdris", "The Great War"],
    "notes": "Appears to be the source of ancient artifacts"
  }}
]

PROSE TO ANALYZE:
{text[:50000]}"""

        result = await self.llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=4000,
            temperature=0.3
        )

        try:
            world_elements = extract_json(result["content"])
            if not isinstance(world_elements, list):
                world_elements = [world_elements] if world_elements else []
        except (json.JSONDecodeError, ValueError):
            world_elements = self._extract_json_from_text(result["content"])

        return {
            "world_elements": world_elements,
            "usage": result["usage"]
        }

    async def extract_style(
        self,
        text: str,
        model: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze prose to extract author's writing style patterns.

        Args:
            text: Prose text to analyze (ideally 5000+ words)
            model: Optional model override
            author_name: Optional author name for personalization

        Returns:
            Dict with 'style_guide' and 'usage' stats
        """
        author_ref = f"the author ({author_name})" if author_name else "the author"

        system_prompt = """You are a literary style analyst who creates detailed style guides by analyzing prose.
Your goal is to capture the author's unique voice so AI can replicate it.
Output valid JSON only, no markdown formatting or explanation."""

        user_prompt = f"""Analyze this prose sample and create a comprehensive style guide for {author_ref}.

Examine and document:

1. SENTENCE_STRUCTURE:
   - Average sentence length (short/medium/long)
   - Variation patterns (do they alternate, cluster, etc.)
   - Use of fragments
   - Complex vs simple sentence preference

2. VOCABULARY:
   - Formality level (casual, literary, academic)
   - Period-specific words
   - Favorite words or phrases that recur
   - Words they notably avoid

3. DIALOGUE:
   - Tag style (said-bookisms vs plain "said")
   - Beat usage (action between dialogue)
   - Dialect or accent representation
   - Interruptions and trailing off

4. POV_STYLE:
   - Narrative distance (deep vs distant)
   - Tense preference
   - Internal monologue style
   - Filter words usage (she felt, he saw, etc.)

5. DESCRIPTION:
   - Sensory balance (which senses emphasized)
   - Metaphor/simile frequency and style
   - Detail density (sparse vs lush)
   - Setting integration approach

6. PACING:
   - Scene length tendencies
   - Transition style
   - Action sequence rhythm
   - Tension building patterns

7. TONE:
   - Emotional register
   - Humor style (if present)
   - Dark/light balance
   - Irony usage

8. DISTINCTIVE_PATTERNS:
   - Any unique stylistic signatures
   - Recurring structural choices
   - Trademark techniques

Output as JSON:
{{
  "author": "{author_name or 'Unknown'}",
  "summary": "Brief 2-3 sentence overall style summary",
  "sentence_structure": {{
    "average_length": "medium",
    "variation": "high - alternates short punchy with flowing complex",
    "fragments": "frequent, for emphasis",
    "complexity": "mixed"
  }},
  "vocabulary": {{
    "formality": "casual literary",
    "period_words": ["specific examples"],
    "favorite_words": ["specific examples"],
    "avoided_words": ["specific examples"]
  }},
  "dialogue": {{
    "tags": "minimal, mostly said/asked",
    "beats": "frequent action beats",
    "dialect": "light accent markers",
    "interruptions": "em-dashes for cuts"
  }},
  "pov_style": {{
    "distance": "deep third",
    "tense": "past",
    "internal_monologue": "italicized direct thoughts",
    "filter_words": "rarely used"
  }},
  "description": {{
    "sensory_focus": ["visual", "tactile"],
    "metaphor_frequency": "moderate",
    "detail_density": "selective - specific telling details",
    "setting_integration": "woven into action"
  }},
  "pacing": {{
    "scene_length": "varies widely",
    "transitions": "hard cuts",
    "action_rhythm": "staccato",
    "tension_building": "slow burn with sharp releases"
  }},
  "tone": {{
    "emotional_register": "controlled intensity",
    "humor": "dry, situational",
    "darkness": "moderate - doesn't shy away",
    "irony": "subtle, character-driven"
  }},
  "distinctive_patterns": [
    "Opens scenes with sensory detail",
    "Ends chapters on unresolved tension",
    "Uses white space for emphasis"
  ],
  "do_not": [
    "Never use 'delve' or 'tapestry'",
    "Avoid filter words",
    "Don't over-explain emotions"
  ],
  "emulate": [
    "Specific techniques to copy"
  ]
}}

PROSE TO ANALYZE:
{text[:60000]}"""

        result = await self.llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=4000,
            temperature=0.4
        )

        try:
            style_guide = extract_json(result["content"])
        except (json.JSONDecodeError, ValueError):
            style_guide = {"error": "Failed to parse style guide", "raw": result["content"][:2000]}

        return {
            "style_guide": style_guide,
            "usage": result["usage"]
        }

    async def analyze_manuscript(
        self,
        text: str,
        model: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive manuscript analysis: characters, world, and style.

        Args:
            text: Full manuscript or large prose sample
            model: Optional model override
            author_name: Optional author name

        Returns:
            Dict with characters, world_elements, style_guide, and combined usage
        """
        # Run all three extractions
        characters_result = await self.extract_characters(text, model)
        world_result = await self.extract_world(text, model)
        style_result = await self.extract_style(text, model, author_name)

        # Combine usage stats
        total_usage = {
            "prompt_tokens": (
                characters_result["usage"]["prompt_tokens"] +
                world_result["usage"]["prompt_tokens"] +
                style_result["usage"]["prompt_tokens"]
            ),
            "completion_tokens": (
                characters_result["usage"]["completion_tokens"] +
                world_result["usage"]["completion_tokens"] +
                style_result["usage"]["completion_tokens"]
            )
        }

        return {
            "characters": characters_result["characters"],
            "world_elements": world_result["world_elements"],
            "style_guide": style_result["style_guide"],
            "usage": total_usage
        }

    async def evaluate_manuscript(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate manuscript quality, pacing, and structure.

        Args:
            text: Manuscript text to evaluate
            model: Optional model override

        Returns:
            Dict with evaluation results and usage stats
        """
        system_prompt = """You are an experienced developmental editor evaluating a manuscript.
Provide constructive, actionable feedback.
Output valid JSON only, no markdown formatting or explanation."""

        user_prompt = f"""Evaluate this manuscript and provide a comprehensive assessment.

Analyze:
1. OVERALL_QUALITY: General impression, strengths, weaknesses
2. PACING: Does it drag or rush? Where?
3. STRUCTURE: Chapter/scene organization, arc progression
4. CHARACTER_DEVELOPMENT: Are characters well-developed?
5. DIALOGUE: Natural? Distinctive voices?
6. PROSE_QUALITY: Sentence-level writing quality
7. CONSISTENCY: Any continuity issues?
8. ENGAGEMENT: Hook, tension, page-turner quality

For each area, rate 1-10 and provide specific feedback.

Output as JSON:
{{
  "summary": "Overall 2-3 sentence assessment",
  "overall_score": 7,
  "areas": {{
    "pacing": {{
      "score": 7,
      "strengths": ["specific examples"],
      "weaknesses": ["specific examples"],
      "recommendations": ["actionable suggestions"]
    }},
    "structure": {{ ... }},
    "character_development": {{ ... }},
    "dialogue": {{ ... }},
    "prose_quality": {{ ... }},
    "consistency": {{ ... }},
    "engagement": {{ ... }}
  }},
  "priority_fixes": [
    "Most important thing to address first",
    "Second priority",
    "Third priority"
  ],
  "strengths_to_preserve": [
    "Things working well that shouldn't be changed"
  ]
}}

MANUSCRIPT TO EVALUATE:
{text[:60000]}"""

        result = await self.llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=4000,
            temperature=0.4
        )

        try:
            evaluation = extract_json(result["content"])
        except (json.JSONDecodeError, ValueError):
            evaluation = {"error": "Failed to parse evaluation", "raw": result["content"][:2000]}

        return {
            "evaluation": evaluation,
            "usage": result["usage"]
        }

    def _extract_json_from_text(self, text: str) -> List[Dict]:
        """Try to extract JSON array from text that may have extra content."""
        # Try to find JSON array in the text
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Try to find JSON object
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                obj = json.loads(match.group())
                return [obj] if isinstance(obj, dict) else obj
            except json.JSONDecodeError:
                pass

        return []


# Global service instance
_extraction_service: Optional[ExtractionService] = None


def get_extraction_service() -> ExtractionService:
    """Get or create the global extraction service instance."""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService()
    return _extraction_service
