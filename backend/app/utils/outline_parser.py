"""Outline parser for importing markdown outlines.

Supports the enhanced outline format with structured scene metadata:
- # Book X: Title (book level - metadata only)
- # Act X: Title (act level)
- ## Chapter X: Title (chapter level)
- ## New Characters Introduced (special section)
- #### Scene X: Title (scene level)

Scene fields parsed:
- POV, Tone, Target, Heat Level, Emotional Arc
- Setting, Beats, Characters, Tags, Notes
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from slugify import slugify


def parse_outline_markdown(markdown_text: str) -> Dict[str, Any]:
    """
    Parse a markdown outline into acts, chapters, scenes, and characters.

    Enhanced format:
    - # Book X: Title = Book level (ignored, metadata only)
    - # Act X: Title = Act level
    - ## Chapter X: Title = Chapter level
    - ## New Characters Introduced = Character definitions section
    - #### Scene X: Title = Scene level with structured fields

    Args:
        markdown_text: The markdown outline text

    Returns:
        Dictionary with 'acts', 'chapters', 'scenes', 'characters', 'book_metadata' lists/dicts
    """
    result = {
        "book_metadata": {},
        "acts": [],
        "chapters": [],
        "scenes": [],
        "characters": []
    }

    lines = markdown_text.strip().split('\n')

    current_act = None
    current_chapter = None
    current_scene = None
    current_character = None
    in_characters_section = False
    scene_content_lines = []
    character_content_lines = []

    act_counter = 0
    chapter_counter = 0
    scene_counter = 0

    def save_current_scene():
        nonlocal current_scene, scene_content_lines
        if current_scene:
            # Parse the scene content for structured fields
            parsed_fields = parse_scene_content('\n'.join(scene_content_lines))
            current_scene.update(parsed_fields)
            result['scenes'].append(current_scene)
            current_scene = None
            scene_content_lines = []

    def save_current_character():
        nonlocal current_character, character_content_lines
        if current_character:
            # Parse character content for metadata
            parsed = parse_character_content('\n'.join(character_content_lines))
            current_character.update(parsed)
            result['characters'].append(current_character)
            current_character = None
            character_content_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines (but collect them for content)
        if not stripped:
            if current_scene:
                scene_content_lines.append('')
            elif current_character:
                character_content_lines.append('')
            i += 1
            continue

        # Check for #### Scene heading (must check before other headings)
        if stripped.startswith('#### '):
            save_current_scene()
            save_current_character()
            in_characters_section = False

            scene_counter += 1
            title = stripped[5:].strip()
            # Remove "Scene X:" prefix if present
            scene_match = re.match(r'Scene\s+\d+[:\s]*(.*)', title, re.IGNORECASE)
            if scene_match and scene_match.group(1):
                title = scene_match.group(1).strip()

            scene_id = generate_id(title, scene_counter)

            current_scene = {
                'id': scene_id,
                'title': title,
                'outline': '',
                'chapter_id': current_chapter['id'] if current_chapter else None,
                'scene_number': scene_counter
            }
            scene_content_lines = []

        # Check for ### character heading (in characters section)
        elif stripped.startswith('### ') and in_characters_section:
            save_current_character()
            char_id = stripped[4:].strip().lower().replace(' ', '-')
            current_character = {
                'id': char_id,
                'name': stripped[4:].strip()
            }
            character_content_lines = []

        # Check for ## heading (chapter or special section)
        elif stripped.startswith('## '):
            save_current_scene()
            save_current_character()

            heading_text = stripped[3:].strip()

            # Check for "New Characters Introduced" section
            if 'new characters' in heading_text.lower():
                in_characters_section = True
                current_chapter = None  # Not a chapter
            else:
                in_characters_section = False
                chapter_counter += 1
                scene_counter = 0  # Reset scene counter for new chapter

                # Parse chapter metadata from following lines
                chapter_metadata = parse_chapter_metadata(lines, i + 1)

                # Parse chapter number from title if present
                chapter_num = chapter_counter
                title = heading_text
                chapter_match = re.match(r'Chapter\s+(\d+)[:\s]*(.*)', heading_text, re.IGNORECASE)
                if chapter_match:
                    chapter_num = int(chapter_match.group(1))
                    title = chapter_match.group(2).strip() or heading_text

                chapter_id = generate_id(title, chapter_num)

                current_chapter = {
                    'id': chapter_id,
                    'title': title,
                    'chapter_number': chapter_num,
                    'act_id': current_act['id'] if current_act else None,
                    'description': '',
                    'pov_pattern': chapter_metadata.get('pov_pattern'),
                    'target_word_count': chapter_metadata.get('target_word_count'),
                    'function': chapter_metadata.get('function')
                }
                result['chapters'].append(current_chapter)

        # Check for # heading (book or act)
        elif stripped.startswith('# '):
            save_current_scene()
            save_current_character()
            in_characters_section = False

            heading_text = stripped[2:].strip()

            # Determine if this is a Book or Act heading
            if heading_text.lower().startswith('book'):
                # Book level - extract metadata
                result['book_metadata'] = parse_book_metadata(lines, i)
            elif heading_text.lower().startswith('act'):
                # Act level
                act_counter += 1
                chapter_counter = 0  # Reset chapter counter for new act
                scene_counter = 0

                # Parse act metadata from following lines
                act_metadata = parse_act_metadata(lines, i + 1)

                # Parse act number from title
                act_num = act_counter
                title = heading_text
                act_match = re.match(r'Act\s+([IVX\d]+)[:\s]*(.*)', heading_text, re.IGNORECASE)
                if act_match:
                    act_num_str = act_match.group(1)
                    act_num = roman_to_int(act_num_str) if act_num_str.isalpha() else int(act_num_str)
                    title = act_match.group(2).strip() or heading_text

                act_id = generate_id(title, act_num)

                current_act = {
                    'id': act_id,
                    'title': title,
                    'act_number': act_num,
                    'description': '',
                    'function': act_metadata.get('function'),
                    'target_word_count': act_metadata.get('target_word_count')
                }
                result['acts'].append(current_act)

        # Regular text - add to current context
        else:
            if current_scene:
                scene_content_lines.append(stripped)
            elif current_character:
                character_content_lines.append(stripped)
            elif current_chapter and not in_characters_section:
                # Text after chapter heading but before any scene = chapter description
                # Skip metadata lines (already parsed)
                if not stripped.startswith('**'):
                    if current_chapter['description']:
                        current_chapter['description'] += '\n' + stripped
                    else:
                        current_chapter['description'] = stripped

        i += 1

    # Don't forget the last items
    save_current_scene()
    save_current_character()

    return result


def parse_scene_content(content: str) -> Dict[str, Any]:
    """
    Parse structured fields from scene content.

    Expected format:
    **POV:** First person - character_id
    **Tone:** tone1, tone2, tone3
    **Target:** 1200 words
    **Heat Level:** sensual (optional)
    **Emotional Arc:** start → end

    [Outline paragraph]

    **Setting:** Location - sensory details

    **Beats:**
    1. Beat one
    2. Beat two

    **Characters:** char1, char2
    **Tags:** tag1, tag2
    **Notes:** Generation notes
    """
    result = {
        'pov': None,
        'tone': None,
        'target_length': None,
        'heat_level': None,
        'emotional_arc': None,
        'setting': None,
        'outline': '',
        'beats': [],
        'character_ids': [],
        'tags': [],
        'generation_notes': None
    }

    lines = content.strip().split('\n')
    outline_lines = []
    in_beats = False
    in_notes = False
    notes_lines = []

    for line in lines:
        stripped = line.strip()

        # Check for field markers
        if stripped.startswith('**POV:**'):
            result['pov'] = stripped[8:].strip()
            in_beats = False
            in_notes = False

        elif stripped.startswith('**Tone:**'):
            result['tone'] = stripped[9:].strip()
            in_beats = False
            in_notes = False

        elif stripped.startswith('**Target:**'):
            target_text = stripped[11:].strip()
            # Extract just the number
            match = re.search(r'(\d+)', target_text)
            if match:
                result['target_length'] = f"{match.group(1)} words"
            else:
                result['target_length'] = target_text
            in_beats = False
            in_notes = False

        elif stripped.startswith('**Heat Level:**'):
            result['heat_level'] = stripped[15:].strip()
            in_beats = False
            in_notes = False

        elif stripped.startswith('**Emotional Arc:**'):
            result['emotional_arc'] = stripped[18:].strip()
            in_beats = False
            in_notes = False

        elif stripped.startswith('**Setting:**'):
            result['setting'] = stripped[12:].strip()
            in_beats = False
            in_notes = False

        elif stripped.startswith('**Beats:**'):
            in_beats = True
            in_notes = False

        elif stripped.startswith('**Characters:**'):
            chars_text = stripped[15:].strip()
            result['character_ids'] = [c.strip() for c in chars_text.split(',') if c.strip()]
            in_beats = False
            in_notes = False

        elif stripped.startswith('**Tags:**'):
            tags_text = stripped[9:].strip()
            result['tags'] = [t.strip() for t in tags_text.split(',') if t.strip()]
            in_beats = False
            in_notes = False

        elif stripped.startswith('**Notes:**'):
            notes_text = stripped[10:].strip()
            if notes_text:
                notes_lines.append(notes_text)
            in_beats = False
            in_notes = True

        elif in_beats:
            # Parse beat lines (numbered or bulleted)
            beat_match = re.match(r'^[\d\.\-\*]+\s*(.*)', stripped)
            if beat_match:
                beat_text = beat_match.group(1).strip()
                if beat_text:
                    result['beats'].append({
                        'id': f"beat-{len(result['beats']) + 1}",
                        'text': beat_text,
                        'order': len(result['beats']) + 1
                    })
            elif stripped:
                # Continuation of previous beat or standalone text
                if result['beats']:
                    result['beats'][-1]['text'] += ' ' + stripped

        elif in_notes:
            # Collect multi-line notes
            if stripped:
                notes_lines.append(stripped)

        elif not stripped.startswith('**') and stripped:
            # Regular outline text
            outline_lines.append(stripped)

    # Compile outline from collected lines
    result['outline'] = '\n'.join(outline_lines).strip()

    # Compile notes
    if notes_lines:
        result['generation_notes'] = ' '.join(notes_lines)

    return result


def parse_chapter_metadata(lines: List[str], start_idx: int) -> Dict[str, Any]:
    """Parse chapter metadata from lines following chapter heading."""
    result = {}

    for i in range(start_idx, min(start_idx + 10, len(lines))):
        line = lines[i].strip()

        if not line:
            continue

        # Stop at next heading
        if line.startswith('#'):
            break

        if line.startswith('**POV Pattern:**'):
            result['pov_pattern'] = line[16:].strip()
        elif line.startswith('**Chapter Target:**'):
            target_text = line[19:].strip()
            match = re.search(r'(\d+)', target_text)
            if match:
                result['target_word_count'] = int(match.group(1))
        elif line.startswith('**Chapter Function:**'):
            result['function'] = line[21:].strip()

    return result


def parse_act_metadata(lines: List[str], start_idx: int) -> Dict[str, Any]:
    """Parse act metadata from lines following act heading."""
    result = {}

    for i in range(start_idx, min(start_idx + 10, len(lines))):
        line = lines[i].strip()

        if not line:
            continue

        # Stop at next heading
        if line.startswith('#'):
            break

        if line.startswith('**Function:**'):
            result['function'] = line[13:].strip()
        elif line.startswith('**Target:**'):
            target_text = line[11:].strip()
            # Handle format like "~35,000 words (Chapters X-Y)"
            match = re.search(r'~?([\d,]+)', target_text)
            if match:
                result['target_word_count'] = int(match.group(1).replace(',', ''))

    return result


def parse_book_metadata(lines: List[str], start_idx: int) -> Dict[str, Any]:
    """Parse book-level metadata."""
    result = {}

    # Get title from first line
    if start_idx < len(lines):
        title_line = lines[start_idx].strip()
        if title_line.startswith('# '):
            title = title_line[2:].strip()
            # Remove "Book X:" prefix
            book_match = re.match(r'Book\s+\d+[:\s]*(.*)', title, re.IGNORECASE)
            if book_match:
                result['title'] = book_match.group(1).strip()
            else:
                result['title'] = title

    # Parse following metadata lines
    for i in range(start_idx + 1, min(start_idx + 15, len(lines))):
        line = lines[i].strip()

        if not line:
            continue

        # Stop at next major heading
        if line.startswith('# ') or line.startswith('## '):
            break

        if line.startswith('**Series:**'):
            result['series'] = line[11:].strip()
        elif line.startswith('**Target Length:**'):
            result['target_length'] = line[18:].strip()
        elif line.startswith('**POV Structure:**'):
            result['pov_structure'] = line[18:].strip()

    return result


def parse_character_content(content: str) -> Dict[str, Any]:
    """Parse character definition content."""
    result = {
        'role': None,
        'description': None,
        'voice': None,
        'first_appearance': None
    }

    for line in content.strip().split('\n'):
        stripped = line.strip()

        if stripped.startswith('**Role:**'):
            result['role'] = stripped[9:].strip()
        elif stripped.startswith('**Description:**'):
            result['description'] = stripped[16:].strip()
        elif stripped.startswith('**Voice:**'):
            result['voice'] = stripped[10:].strip()
        elif stripped.startswith('**First Appearance:**'):
            result['first_appearance'] = stripped[21:].strip()

    return result


def generate_id(title: str, counter: int) -> str:
    """Generate a URL-safe ID from a title."""
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
        warnings.append("No chapters or scenes found. Check heading format: ## for chapters, #### for scenes.")

    if parsed['scenes'] and not parsed['chapters']:
        warnings.append("Scenes found but no chapters. Scenes will not be assigned to chapters.")

    # Check for scenes without outlines
    for scene in parsed['scenes']:
        if not scene.get('outline'):
            warnings.append(f"Scene '{scene['title']}' has no outline text.")

    # Check for missing recommended fields
    for scene in parsed['scenes']:
        if not scene.get('pov'):
            warnings.append(f"Scene '{scene['title']}' has no POV specified.")
        if not scene.get('beats'):
            warnings.append(f"Scene '{scene['title']}' has no beats defined.")

    # Check for duplicate IDs
    all_ids = set()
    for item_type in ['acts', 'chapters', 'scenes']:
        for item in parsed[item_type]:
            if item['id'] in all_ids:
                warnings.append(f"Duplicate ID generated: {item['id']}")
            all_ids.add(item['id'])

    return warnings
