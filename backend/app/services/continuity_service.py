"""Continuity Checking Service - detects contradictions with established canon."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.memory_service import memory_service
from app.config import settings


class ContinuityIssue(BaseModel):
    """A potential continuity issue detected."""

    severity: str = Field(..., description="low, medium, or high")
    category: str = Field(..., description="character, world, timeline, or general")
    issue: str = Field(..., description="Description of the contradiction")
    established_fact: str = Field(..., description="The canon fact being contradicted")
    source_scene: Optional[str] = Field(None, description="Scene where fact was established")
    suggestion: Optional[str] = Field(None, description="Suggested fix")


class ContinuityCheckResult(BaseModel):
    """Result of a continuity check."""

    issues: List[ContinuityIssue] = Field(default_factory=list)
    checked_against: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of facts checked per category"
    )
    has_issues: bool = Field(default=False)


class ContinuityService:
    """Service for checking prose against established canon."""

    async def check_continuity(
        self,
        series_id: str,
        prose_text: str,
        scene_context: Optional[str] = None,
        model: Optional[str] = None
    ) -> ContinuityCheckResult:
        """
        Check prose text for potential continuity issues against series memory.

        Args:
            series_id: Series to check against
            prose_text: The prose to check
            scene_context: Optional scene outline for context
            model: Optional model override

        Returns:
            ContinuityCheckResult with any detected issues
        """
        from app.services.llm_service import get_llm_service
        llm = get_llm_service()

        # Load memory
        memory = memory_service.get_memory(series_id)
        if not memory:
            return ContinuityCheckResult(
                issues=[],
                checked_against={},
                has_issues=False
            )

        # Build facts context
        facts_context = self._build_facts_context(memory)

        if not facts_context["total_facts"]:
            return ContinuityCheckResult(
                issues=[],
                checked_against=facts_context["counts"],
                has_issues=False
            )

        # Use LLM to detect contradictions
        system_prompt = """You are a continuity editor checking prose for contradictions with established facts.

Your job is to identify any statements in the prose that contradict the established facts.

Be precise. Only flag clear contradictions, not:
- Events that happen AFTER the established facts (character development is allowed)
- Vague or ambiguous statements
- Minor details that don't affect the story

For each issue, rate severity:
- high: Major plot or character contradiction that readers would notice
- medium: Noticeable inconsistency but recoverable
- low: Minor detail inconsistency

Respond in JSON format:
{
    "issues": [
        {
            "severity": "high|medium|low",
            "category": "character|world|timeline|general",
            "issue": "Description of the contradiction found",
            "established_fact": "The specific fact being contradicted",
            "source_scene": "scene-id if known",
            "suggestion": "How to fix it"
        }
    ]
}

If no issues found, respond with: {"issues": []}"""

        context = scene_context + "\n\n" if scene_context else ""

        user_prompt = f"""Check this prose for continuity issues against the established facts.

ESTABLISHED FACTS:

{facts_context["text"]}

PROSE TO CHECK:

{context}{prose_text}

Check for any contradictions with the established facts above. Return your findings as JSON."""

        result = await llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=2000,
            temperature=0.2
        )

        # Parse response
        from app.utils.prompt_templates import extract_json
        response_data = extract_json(result["content"])

        issues = []
        if response_data and "issues" in response_data:
            for issue_data in response_data["issues"]:
                try:
                    issues.append(ContinuityIssue(**issue_data))
                except Exception:
                    # Skip malformed issues
                    pass

        return ContinuityCheckResult(
            issues=issues,
            checked_against=facts_context["counts"],
            has_issues=len(issues) > 0
        )

    def _build_facts_context(self, memory) -> Dict[str, Any]:
        """Build a facts context string from memory."""
        sections = []
        counts = {
            "character_states": 0,
            "world_facts": 0,
            "timeline": 0
        }

        # Character facts
        if memory.character_changes:
            char_facts = []
            by_char: Dict[str, List] = {}
            for change in memory.character_changes:
                if change.character_name not in by_char:
                    by_char[change.character_name] = []
                by_char[change.character_name].append(change)

            for char_name, changes in by_char.items():
                facts = [f"- {c.change_type}: {c.description}" for c in changes]
                char_facts.append(f"### {char_name}\n" + "\n".join(facts))

            counts["character_states"] = len(memory.character_changes)
            sections.append("## CHARACTER FACTS\n\n" + "\n\n".join(char_facts))

        # World facts
        if memory.world_facts:
            by_cat: Dict[str, List] = {}
            for fact in memory.world_facts:
                cat = fact.category or "general"
                if cat not in by_cat:
                    by_cat[cat] = []
                by_cat[cat].append(fact)

            world_sections = []
            for cat, facts in by_cat.items():
                fact_list = [f"- {f.fact}" for f in facts]
                world_sections.append(f"### {cat.title()}\n" + "\n".join(fact_list))

            counts["world_facts"] = len(memory.world_facts)
            sections.append("## WORLD FACTS\n\n" + "\n\n".join(world_sections))

        # Timeline events
        if memory.timeline:
            events = [f"- {e.event}" for e in memory.timeline]
            counts["timeline"] = len(memory.timeline)
            sections.append("## TIMELINE EVENTS\n\n" + "\n".join(events))

        total = sum(counts.values())

        return {
            "text": "\n\n".join(sections) if sections else "",
            "counts": counts,
            "total_facts": total
        }


# Singleton instance
continuity_service = ContinuityService()


def get_continuity_service() -> ContinuityService:
    """Get the continuity service instance."""
    return continuity_service
