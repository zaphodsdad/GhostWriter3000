"""Style Learning Service - learns writing preferences from user edits.

This service analyzes the difference between AI-generated prose and user-edited
prose to learn author preferences. These preferences are then applied to
future generations to better match the author's style.

Key capabilities:
- Detect vocabulary preferences (word replacements, avoided words)
- Detect sentence structure preferences (length, complexity)
- Detect dialogue style preferences
- Detect pacing preferences
- Store and retrieve preferences per series
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from difflib import SequenceMatcher, unified_diff

from app.models.memory import (
    StylePreference,
    EditAnalysis,
    StyleMemory,
)
from app.config import settings


class StyleLearningService:
    """Service for learning writing preferences from user edits."""

    def __init__(self):
        pass

    def _style_dir(self, series_id: str) -> Path:
        """Get the style learning directory for a series."""
        return settings.series_path(series_id) / "memory" / "style"

    def _ensure_style_dir(self, series_id: str) -> Path:
        """Ensure style directory exists and return path."""
        style_dir = self._style_dir(series_id)
        style_dir.mkdir(parents=True, exist_ok=True)
        return style_dir

    def _style_memory_path(self, series_id: str) -> Path:
        """Get path to style_memory.json."""
        return self._style_dir(series_id) / "style_memory.json"

    def load_style_memory(self, series_id: str) -> StyleMemory:
        """Load or create style memory for a series."""
        style_path = self._style_memory_path(series_id)
        if style_path.exists():
            data = json.loads(style_path.read_text(encoding="utf-8"))
            return StyleMemory(**data)
        return StyleMemory(series_id=series_id)

    def save_style_memory(self, series_id: str, memory: StyleMemory):
        """Save style memory to disk."""
        self._ensure_style_dir(series_id)
        style_path = self._style_memory_path(series_id)
        style_path.write_text(
            json.dumps(memory.model_dump(), default=str, indent=2),
            encoding="utf-8"
        )

    def analyze_edit(
        self,
        series_id: str,
        scene_id: str,
        book_id: str,
        original_text: str,
        edited_text: str
    ) -> List[EditAnalysis]:
        """
        Analyze the difference between original and edited text.

        Detects patterns in user edits to learn preferences:
        - Word replacements
        - Sentence restructuring
        - Deletions (what the author removes)
        - Additions (what the author adds)

        Args:
            series_id: Series these edits belong to
            scene_id: Scene that was edited
            book_id: Book containing the scene
            original_text: Text before user edit
            edited_text: Text after user edit

        Returns:
            List of EditAnalysis objects describing detected patterns
        """
        analyses = []

        # Tokenize into words for vocabulary analysis
        word_changes = self._detect_word_changes(original_text, edited_text)
        for old_word, new_word, count in word_changes:
            analyses.append(EditAnalysis(
                scene_id=scene_id,
                book_id=book_id,
                original_text=old_word,
                edited_text=new_word,
                edit_type="word_change",
                detected_pattern=f"Replaces '{old_word}' with '{new_word}' ({count}x)"
            ))

        # Detect sentence-level changes
        sentence_changes = self._detect_sentence_changes(original_text, edited_text)
        for change in sentence_changes:
            analyses.append(EditAnalysis(
                scene_id=scene_id,
                book_id=book_id,
                original_text=change["original"],
                edited_text=change["edited"],
                edit_type=change["type"],
                detected_pattern=change["pattern"]
            ))

        # Detect deletions (words/phrases consistently removed)
        deletions = self._detect_deletions(original_text, edited_text)
        for deleted_phrase in deletions:
            analyses.append(EditAnalysis(
                scene_id=scene_id,
                book_id=book_id,
                original_text=deleted_phrase,
                edited_text="",
                edit_type="deletion",
                detected_pattern=f"Removes: '{deleted_phrase}'"
            ))

        return analyses

    def _detect_word_changes(
        self,
        original: str,
        edited: str
    ) -> List[Tuple[str, str, int]]:
        """Detect word-for-word replacements."""
        changes = []

        # Normalize and split into words
        orig_words = re.findall(r'\b\w+\b', original.lower())
        edit_words = re.findall(r'\b\w+\b', edited.lower())

        # Use SequenceMatcher to find replacements
        matcher = SequenceMatcher(None, orig_words, edit_words)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                # Simple case: single word replaced with single word
                if i2 - i1 == 1 and j2 - j1 == 1:
                    old_word = orig_words[i1]
                    new_word = edit_words[j1]
                    # Only track if it's a meaningful change (not just typo fix)
                    if len(old_word) > 2 and len(new_word) > 2:
                        # Check if this looks like a vocabulary preference
                        if not self._is_typo_fix(old_word, new_word):
                            changes.append((old_word, new_word, 1))

        # Merge duplicates and count
        change_counts: Dict[Tuple[str, str], int] = {}
        for old, new, _ in changes:
            key = (old, new)
            change_counts[key] = change_counts.get(key, 0) + 1

        return [(old, new, count) for (old, new), count in change_counts.items()]

    def _is_typo_fix(self, old: str, new: str) -> bool:
        """Check if a word change is likely just a typo fix."""
        # Very similar words (edit distance 1-2) are likely typos
        if len(old) == len(new):
            diffs = sum(1 for a, b in zip(old, new) if a != b)
            if diffs <= 2:
                return True

        # Transposition
        if len(old) == len(new) == len(set(old)) == len(set(new)):
            if sorted(old) == sorted(new):
                return True

        return False

    def _detect_sentence_changes(
        self,
        original: str,
        edited: str
    ) -> List[Dict[str, str]]:
        """Detect sentence-level changes."""
        changes = []

        # Split into sentences
        orig_sentences = re.split(r'(?<=[.!?])\s+', original)
        edit_sentences = re.split(r'(?<=[.!?])\s+', edited)

        # Compare sentence lengths
        orig_avg_len = sum(len(s.split()) for s in orig_sentences) / max(1, len(orig_sentences))
        edit_avg_len = sum(len(s.split()) for s in edit_sentences) / max(1, len(edit_sentences))

        if abs(orig_avg_len - edit_avg_len) > 5:
            if edit_avg_len < orig_avg_len:
                changes.append({
                    "original": f"Average sentence: {orig_avg_len:.0f} words",
                    "edited": f"Average sentence: {edit_avg_len:.0f} words",
                    "type": "sentence_restructure",
                    "pattern": "Prefers shorter sentences"
                })
            else:
                changes.append({
                    "original": f"Average sentence: {orig_avg_len:.0f} words",
                    "edited": f"Average sentence: {edit_avg_len:.0f} words",
                    "type": "sentence_restructure",
                    "pattern": "Prefers longer sentences"
                })

        return changes

    def _detect_deletions(
        self,
        original: str,
        edited: str
    ) -> List[str]:
        """Detect phrases that were deleted."""
        deletions = []

        # Common filler phrases that might be deleted
        filler_patterns = [
            r'\b(very|really|just|quite|rather|somewhat|slightly)\b',
            r'\b(began to|started to|proceeded to)\b',
            r'\b(in order to|for the purpose of)\b',
            r'\b(it was|there was|there were)\b',
            r'\b(suddenly|immediately|quickly)\b',
        ]

        for pattern in filler_patterns:
            orig_matches = len(re.findall(pattern, original, re.IGNORECASE))
            edit_matches = len(re.findall(pattern, edited, re.IGNORECASE))

            if orig_matches > edit_matches:
                # This pattern was reduced
                match = re.search(pattern, original, re.IGNORECASE)
                if match:
                    deletions.append(match.group())

        return list(set(deletions))

    async def learn_from_edit(
        self,
        series_id: str,
        scene_id: str,
        book_id: str,
        original_text: str,
        edited_text: str,
        model: Optional[str] = None
    ) -> StyleMemory:
        """
        Learn from a user edit and update style preferences.

        This is the main entry point for style learning. It:
        1. Analyzes the edit for patterns
        2. Updates or creates style preferences
        3. Saves to disk

        Args:
            series_id: Series these preferences apply to
            scene_id: Scene that was edited
            book_id: Book containing the scene
            original_text: Text before user edit
            edited_text: Text after user edit
            model: Optional model for advanced analysis

        Returns:
            Updated StyleMemory
        """
        # Skip if texts are too similar
        similarity = SequenceMatcher(None, original_text, edited_text).ratio()
        if similarity > 0.98:
            return self.load_style_memory(series_id)

        # Analyze the edit
        analyses = self.analyze_edit(series_id, scene_id, book_id, original_text, edited_text)

        # Load existing style memory
        memory = self.load_style_memory(series_id)

        # Update preferences based on analyses
        for analysis in analyses:
            self._update_preferences_from_analysis(memory, analysis)

        # Save edit to history
        for analysis in analyses:
            memory.edit_history.append(analysis)
            # Keep history manageable
            if len(memory.edit_history) > 100:
                memory.edit_history = memory.edit_history[-100:]

        memory.last_learned = datetime.utcnow()

        # Optionally use LLM for deeper analysis
        if model and len(analyses) > 0:
            await self._llm_analyze_patterns(memory, original_text, edited_text, model)

        # Save updated memory
        self.save_style_memory(series_id, memory)

        return memory

    def _update_preferences_from_analysis(
        self,
        memory: StyleMemory,
        analysis: EditAnalysis
    ):
        """Update preferences based on a single edit analysis."""

        if analysis.edit_type == "word_change":
            # Extract words from the pattern
            old_word = analysis.original_text.lower()
            new_word = analysis.edited_text.lower()

            if old_word and new_word:
                # Check if we already have this preference
                if old_word in memory.preferred_vocabulary:
                    # Reinforce if same replacement
                    if memory.preferred_vocabulary[old_word] == new_word:
                        # Increase confidence of related preference
                        for pref in memory.preferences:
                            if pref.category == "vocabulary" and old_word in pref.preference:
                                pref.confidence = min(1.0, pref.confidence + 0.1)
                                pref.learned_from_count += 1
                                pref.last_reinforced = datetime.utcnow()
                else:
                    memory.preferred_vocabulary[old_word] = new_word
                    memory.preferences.append(StylePreference(
                        category="vocabulary",
                        preference=f"Use '{new_word}' instead of '{old_word}'",
                        confidence=0.5,
                        examples=[analysis.detected_pattern or ""],
                        learned_from_count=1
                    ))

        elif analysis.edit_type == "deletion":
            deleted = analysis.original_text.lower()
            if deleted and deleted not in memory.avoided_vocabulary:
                memory.avoided_vocabulary.append(deleted)

        elif analysis.edit_type == "sentence_restructure":
            if analysis.detected_pattern:
                # Check for existing preference
                existing = None
                for pref in memory.preferences:
                    if pref.category == "sentence_structure" and pref.preference == analysis.detected_pattern:
                        existing = pref
                        break

                if existing:
                    existing.confidence = min(1.0, existing.confidence + 0.1)
                    existing.learned_from_count += 1
                    existing.last_reinforced = datetime.utcnow()
                else:
                    memory.preferences.append(StylePreference(
                        category="sentence_structure",
                        preference=analysis.detected_pattern,
                        confidence=0.4,
                        examples=[f"Changed from: {analysis.original_text}"],
                        learned_from_count=1
                    ))

    async def _llm_analyze_patterns(
        self,
        memory: StyleMemory,
        original: str,
        edited: str,
        model: str
    ):
        """Use LLM for deeper pattern analysis."""
        from app.services.llm_service import get_llm_service
        from app.utils.prompt_templates import extract_json

        llm = get_llm_service()

        # Only analyze if texts are substantively different
        if len(original) < 100 or len(edited) < 100:
            return

        system_prompt = """You are a writing style analyst. Analyze the changes between original and edited text
to identify the author's writing preferences. Focus on:
- Vocabulary choices (specific words preferred/avoided)
- Sentence structure (length, complexity)
- Dialogue style
- Description style
- Pacing preferences

Output JSON only."""

        user_prompt = f"""Compare these two versions of prose and identify style preferences:

ORIGINAL:
{original[:3000]}

EDITED BY AUTHOR:
{edited[:3000]}

What writing preferences does the author demonstrate? Output as JSON:
{{
  "vocabulary_preferences": [
    {{"avoid": "word1", "prefer": "word2", "reason": "why"}}
  ],
  "sentence_preferences": [
    {{"preference": "description", "confidence": 0.5-1.0}}
  ],
  "dialogue_preferences": [
    {{"preference": "description", "confidence": 0.5-1.0}}
  ],
  "pacing_preferences": [
    {{"preference": "description", "confidence": 0.5-1.0}}
  ]
}}

Only include preferences you're confident about. Use empty arrays for uncertain categories."""

        try:
            result = await llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=model,
                max_tokens=1000,
                temperature=0.2
            )

            data = extract_json(result["content"])

            # Add vocabulary preferences
            for vocab in data.get("vocabulary_preferences", []):
                avoid = vocab.get("avoid", "").lower()
                prefer = vocab.get("prefer", "").lower()
                if avoid and prefer and avoid not in memory.preferred_vocabulary:
                    memory.preferred_vocabulary[avoid] = prefer

            # Add other preferences
            for pref_type, category in [
                ("sentence_preferences", "sentence_structure"),
                ("dialogue_preferences", "dialogue"),
                ("pacing_preferences", "pacing")
            ]:
                for pref in data.get(pref_type, []):
                    preference = pref.get("preference", "")
                    confidence = float(pref.get("confidence", 0.5))

                    if preference and confidence >= 0.5:
                        # Check for duplicate
                        is_duplicate = any(
                            p.preference.lower() == preference.lower()
                            for p in memory.preferences
                            if p.category == category
                        )
                        if not is_duplicate:
                            memory.preferences.append(StylePreference(
                                category=category,
                                preference=preference,
                                confidence=confidence,
                                examples=[],
                                learned_from_count=1
                            ))

        except Exception:
            # LLM analysis is optional, don't fail on errors
            pass

    def get_preferences_for_prompt(self, series_id: str) -> str:
        """Get style preferences formatted for inclusion in generation prompts."""
        memory = self.load_style_memory(series_id)
        return memory.get_preferences_summary()

    def clear_style_memory(self, series_id: str):
        """Clear all learned style preferences for a series."""
        memory = StyleMemory(series_id=series_id)
        self.save_style_memory(series_id, memory)


# Singleton instance
style_learning_service = StyleLearningService()


def get_style_learning_service() -> StyleLearningService:
    """Get the singleton StyleLearningService instance."""
    return style_learning_service
