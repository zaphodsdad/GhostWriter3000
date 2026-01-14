"""Prompt templates for Claude API interactions."""

import re
from typing import List, Dict, Any


# Common AI preamble patterns to strip from output
AI_PREAMBLE_PATTERNS = [
    r"^Here'?s?\s+(a\s+)?(the\s+)?(narrative\s+)?(prose\s+)?(draft\s+)?(for\s+)?(scene\s+)?[\d\w\-:]*\s*[:.]?\s*\n*",
    r"^Here\s+is\s+(a\s+)?(the\s+)?(narrative\s+)?(prose\s+)?(draft\s+)?(for\s+)?(scene\s+)?[\d\w\-:]*\s*[:.]?\s*\n*",
    r"^I'?ll\s+write\s+.*?[:.]?\s*\n*",
    r"^Let\s+me\s+write\s+.*?[:.]?\s*\n*",
    r"^This\s+is\s+(a\s+)?(the\s+)?scene.*?[:.]?\s*\n*",
    r"^Scene\s+\d+[:.]?\s*\n*",
    r"^#\s*Scene\s+\d+.*?\n*",
    r"^---+\s*\n*",
]


def clean_prose_output(prose: str) -> str:
    """
    Clean AI-generated prose by removing common preambles and artifacts.

    Args:
        prose: Raw prose output from LLM

    Returns:
        Cleaned prose with preambles stripped
    """
    if not prose:
        return prose

    cleaned = prose.strip()

    # Apply each pattern
    for pattern in AI_PREAMBLE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

    # Strip any leading/trailing whitespace that resulted from cleanup
    cleaned = cleaned.strip()

    # Remove leading blank lines
    while cleaned.startswith("\n"):
        cleaned = cleaned[1:]

    return cleaned


def build_system_prompt(
    characters: List[Dict[str, Any]],
    world_contexts: List[Dict[str, Any]],
    previous_scene_summaries: List[Dict[str, Any]] = None,
    style_guide: Dict[str, Any] = None
) -> str:
    """
    Build system prompt with character, world context, previous scene summaries, and style guide.

    Args:
        characters: List of character data dictionaries
        world_contexts: List of world context data dictionaries
        previous_scene_summaries: List of previous scene summaries for continuity
        style_guide: Style guide dictionary with pov, tense, tone, heat_level, guide

    Returns:
        Formatted system prompt
    """
    prompt_parts = [
        "You are a skilled creative writer specializing in narrative prose.",
        "Use the following information to inform your writing.",
        ""
    ]

    # Add style guide at the top (most important for shaping output)
    if style_guide:
        prompt_parts.append("# STYLE GUIDE\n")
        prompt_parts.append("**CRITICAL: Follow this style guide exactly. It defines the voice, tone, and rules for this project.**\n")

        # Quick reference fields
        if style_guide.get('pov'):
            prompt_parts.append(f"**Point of View:** {style_guide['pov']}")
        if style_guide.get('tense'):
            prompt_parts.append(f"**Tense:** {style_guide['tense']}")
        if style_guide.get('tone'):
            prompt_parts.append(f"**Tone:** {style_guide['tone']}")
        if style_guide.get('heat_level'):
            prompt_parts.append(f"**Heat Level:** {style_guide['heat_level']}")

        # Full guide content
        if style_guide.get('guide'):
            prompt_parts.append("\n## Full Style Guide\n")
            prompt_parts.append(style_guide['guide'])
            prompt_parts.append("")

        prompt_parts.append("")

    # Add previous scene summaries for continuity
    if previous_scene_summaries:
        prompt_parts.append("# STORY SO FAR\n")
        prompt_parts.append("The following scenes have already occurred in this story:\n")
        for i, scene_summary in enumerate(previous_scene_summaries, 1):
            scene_title = scene_summary.get('title', f'Scene {i}')
            summary = scene_summary.get('summary', '')
            prompt_parts.append(f"## {scene_title}\n{summary}\n")
        prompt_parts.append("")

    if characters:
        prompt_parts.append("# CHARACTER INFORMATION\n")
        for char in characters:
            prompt_parts.append(f"## {char.get('metadata', {}).get('name', 'Character')}\n")
            prompt_parts.append(f"**Metadata:**\n{format_metadata(char.get('metadata', {}))}\n")
            prompt_parts.append(f"**Details:**\n{char.get('content', '')}\n")

    if world_contexts:
        prompt_parts.append("\n# WORLD CONTEXT\n")
        for world in world_contexts:
            prompt_parts.append(f"## {world.get('metadata', {}).get('name', 'World')}\n")
            prompt_parts.append(f"**Metadata:**\n{format_metadata(world.get('metadata', {}))}\n")
            prompt_parts.append(f"**Details:**\n{world.get('content', '')}\n")

    return "\n".join(prompt_parts)


def build_generation_prompt(scene_outline: Dict[str, Any]) -> str:
    """
    Build prompt for initial prose generation.

    Args:
        scene_outline: Scene data dictionary

    Returns:
        Formatted generation prompt
    """
    parts = [
        "Generate narrative prose for the following scene:",
        "",
        f"# {scene_outline.get('title', 'Untitled Scene')}",
        "",
        f"**Outline:** {scene_outline.get('outline', '')}",
        ""
    ]

    if scene_outline.get('tone'):
        parts.append(f"**Tone:** {scene_outline['tone']}")

    if scene_outline.get('pov'):
        parts.append(f"**Point of View:** {scene_outline['pov']}")

    if scene_outline.get('target_length'):
        parts.append(f"**Target Length:** {scene_outline['target_length']}")

    if scene_outline.get('additional_notes'):
        parts.append(f"\n**Additional Notes:** {scene_outline['additional_notes']}")

    parts.extend([
        "",
        "Write the prose for this scene, incorporating the character and world context provided in the system prompt.",
        "Focus on vivid descriptions, authentic character voices, and engaging narrative flow.",
        "",
        "CRITICAL: Output ONLY the prose itself. Do not include:",
        "- Any preamble or introduction (e.g., \"Here's the scene...\", \"Here is the narrative...\")",
        "- Meta-commentary about what you're writing",
        "- Section headers or titles within the prose",
        "- Closing remarks or summaries",
        "",
        "Begin directly with the story content. The first words should be narrative prose."
    ])

    return "\n".join(parts)


def build_critique_prompt(prose: str, style_guide: Dict[str, Any] = None) -> str:
    """
    Build prompt for critiquing generated prose.

    Args:
        prose: The prose text to critique
        style_guide: Optional style guide to critique against

    Returns:
        Formatted critique prompt
    """
    style_section = ""
    if style_guide and style_guide.get('guide'):
        style_section = f"""
# STYLE GUIDE REFERENCE
The prose should conform to this style guide:

{style_guide.get('guide', '')}

---

"""

    return f"""Please provide a constructive critique of the following prose:

---
{prose}
---
{style_section}
Evaluate the prose on these dimensions:

1. **Narrative Flow**: Does the scene progress smoothly and logically?
2. **Character Voice**: Are character voices distinct and authentic?
3. **Sensory Details**: Are there vivid, engaging descriptions?
4. **Pacing**: Is the pacing appropriate for the scene's purpose?
5. **Tone**: Does the tone match the intended mood?
6. **Technical Writing**: Are there issues with grammar, repetition, or word choice?
7. **Style Guide Compliance**: Does the prose follow the style guide rules? Look for banned constructions, AI tells, and voice requirements.

For each area, provide:
- What works well
- What could be improved
- Specific suggestions for revision

Be constructive but honest. If something is working well, say so. If something needs improvement, explain why and how to fix it. Pay special attention to any style guide violations."""


def build_revision_prompt(original_prose: str, critique: str) -> str:
    """
    Build prompt for revising prose based on critique.

    Args:
        original_prose: The original prose text
        critique: The critique of the original prose

    Returns:
        Formatted revision prompt
    """
    return f"""Please revise the following prose based on the critique provided.

# Original Prose
---
{original_prose}
---

# Critique
---
{critique}
---

# Instructions
Revise the prose to address the critique's suggestions while maintaining:
- The core narrative and plot points
- Character consistency
- World building elements

Focus on improving the specific areas mentioned in the critique. Output only the revised prose, without commentary."""


def build_summary_prompt(scene_title: str, prose: str) -> str:
    """
    Build prompt for generating a scene summary.

    Args:
        scene_title: Title of the scene
        prose: The final prose text to summarize

    Returns:
        Formatted summary generation prompt
    """
    return f"""Generate a concise summary of the following scene for continuity tracking.

# Scene: {scene_title}

# Prose:
---
{prose}
---

# Instructions:
Create a summary (300-500 words) that captures:

1. **Key Events**: What happened in this scene? What plot points were advanced?
2. **Character Development**: How did characters change or reveal themselves?
3. **Emotional Beats**: What were the key emotional moments?
4. **World State Changes**: Did anything change in the world or setting?
5. **Open Threads**: What questions or conflicts were raised but not resolved?
6. **Continuity Details**: Specific facts, locations, or objects that future scenes should remember

Write the summary in past tense, as if you're documenting what already happened. Be specific about names, places, and key details that maintain continuity.

Output only the summary, without commentary or section headers."""


def format_metadata(metadata: Dict[str, Any]) -> str:
    """
    Format metadata dictionary as readable text.

    Args:
        metadata: Metadata dictionary

    Returns:
        Formatted string
    """
    lines = []
    for key, value in metadata.items():
        if isinstance(value, list):
            lines.append(f"- **{key}**: {', '.join(str(v) for v in value)}")
        elif isinstance(value, dict):
            lines.append(f"- **{key}**:")
            for sub_key, sub_value in value.items():
                lines.append(f"  - {sub_key}: {sub_value}")
        else:
            lines.append(f"- **{key}**: {value}")
    return "\n".join(lines)
