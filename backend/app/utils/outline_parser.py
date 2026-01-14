"""Outline parser for importing markdown outlines."""

import re
from typing import List, Dict, Any, Optional
from slugify import slugify


def parse_outline_markdown(markdown_text: str) -> Dict[str, Any]:
    """
    Parse a markdown outline into acts, chapters, and scenes.

    Format:
    - # = Act (optional)
    - ## = Chapter
    - ### = Scene (text below = outline)

    Args:
        markdown_text: The markdown outline text

    Returns:
        Dictionary with 'acts', 'chapters', 'scenes' lists
    """
    result = {
        "acts": [],
        "chapters": [],
        "scenes": []
    }

    lines = markdown_text.strip().split('\n')

    current_act = None
    current_chapter = None
    current_scene = None
    scene_outline_lines = []

    act_counter = 0
    chapter_counter = 0
    scene_counter = 0

    def save_current_scene():
        nonlocal current_scene, scene_outline_lines
        if current_scene:
            outline = '\n'.join(scene_outline_lines).strip()
            if outline:
                current_scene['outline'] = outline
            result['scenes'].append(current_scene)
            current_scene = None
            scene_outline_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines unless we're collecting scene outline
        if not stripped:
            if current_scene:
                scene_outline_lines.append('')
            continue

        # Check for headings
        if stripped.startswith('### '):
            # Scene heading
            save_current_scene()
            scene_counter += 1
            title = stripped[4:].strip()
            scene_id = generate_id(title, scene_counter)

            current_scene = {
                'id': scene_id,
                'title': title,
                'outline': '',
                'chapter_id': current_chapter['id'] if current_chapter else None,
                'scene_number': scene_counter
            }
            scene_outline_lines = []

        elif stripped.startswith('## '):
            # Chapter heading
            save_current_scene()
            chapter_counter += 1
            scene_counter = 0  # Reset scene counter for new chapter
            title = stripped[3:].strip()
            chapter_id = generate_id(title, chapter_counter)

            # Parse chapter number from title if present (e.g., "Chapter 1: Title")
            chapter_num = chapter_counter
            chapter_match = re.match(r'Chapter\s+(\d+)[:\s]*(.*)', title, re.IGNORECASE)
            if chapter_match:
                chapter_num = int(chapter_match.group(1))
                title = chapter_match.group(2).strip() or title

            current_chapter = {
                'id': chapter_id,
                'title': title,
                'chapter_number': chapter_num,
                'act_id': current_act['id'] if current_act else None,
                'description': ''
            }
            result['chapters'].append(current_chapter)

        elif stripped.startswith('# '):
            # Act heading
            save_current_scene()
            act_counter += 1
            chapter_counter = 0  # Reset chapter counter for new act
            title = stripped[2:].strip()
            act_id = generate_id(title, act_counter)

            # Parse act number from title if present (e.g., "Act I: Title" or "Act 1: Title")
            act_num = act_counter
            act_match = re.match(r'Act\s+([IVX\d]+)[:\s]*(.*)', title, re.IGNORECASE)
            if act_match:
                act_num_str = act_match.group(1)
                # Convert Roman numerals if needed
                act_num = roman_to_int(act_num_str) if act_num_str.isalpha() else int(act_num_str)
                title = act_match.group(2).strip() or title

            current_act = {
                'id': act_id,
                'title': title,
                'act_number': act_num,
                'description': ''
            }
            result['acts'].append(current_act)

        else:
            # Regular text - add to current scene outline or chapter description
            if current_scene:
                scene_outline_lines.append(stripped)
            elif current_chapter and not current_scene:
                # Text after chapter heading but before any scene = chapter description
                if current_chapter['description']:
                    current_chapter['description'] += '\n' + stripped
                else:
                    current_chapter['description'] = stripped

    # Don't forget the last scene
    save_current_scene()

    return result


def generate_id(title: str, counter: int) -> str:
    """Generate a URL-safe ID from a title."""
    # Use slugify to create a clean ID
    base_id = slugify(title, max_length=50, lowercase=True)
    if not base_id:
        base_id = f"item-{counter}"
    return base_id


def roman_to_int(s: str) -> int:
    """Convert Roman numeral to integer."""
    roman_values = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000
    }
    s = s.upper()
    total = 0
    prev = 0
    for char in reversed(s):
        val = roman_values.get(char, 0)
        if val < prev:
            total -= val
        else:
            total += val
        prev = val
    return total if total > 0 else 1


def validate_outline(parsed: Dict[str, Any]) -> List[str]:
    """
    Validate a parsed outline and return any warnings.

    Args:
        parsed: The parsed outline dictionary

    Returns:
        List of warning messages (empty if no issues)
    """
    warnings = []

    if not parsed['chapters'] and not parsed['scenes']:
        warnings.append("No chapters or scenes found. Make sure to use ## for chapters and ### for scenes.")

    if parsed['scenes'] and not parsed['chapters']:
        warnings.append("Scenes found but no chapters. Scenes will not be assigned to chapters.")

    # Check for scenes without outlines
    for scene in parsed['scenes']:
        if not scene.get('outline'):
            warnings.append(f"Scene '{scene['title']}' has no outline text.")

    # Check for duplicate IDs
    all_ids = []
    for item_type in ['acts', 'chapters', 'scenes']:
        for item in parsed[item_type]:
            if item['id'] in all_ids:
                warnings.append(f"Duplicate ID generated: {item['id']}")
            all_ids.append(item['id'])

    return warnings
