"""Grammar and style checking service using LanguageTool."""

import logging
from typing import List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Lazy import to handle cases where Java isn't installed
_language_tool = None
_tool_initialized = False
_init_error = None


class GrammarIssue(BaseModel):
    """A single grammar/style issue."""

    message: str  # Human-readable description
    short_message: str  # Brief description (e.g., "Possible typo")
    offset: int  # Character offset in text
    length: int  # Length of problematic text
    replacements: List[str]  # Suggested fixes (may be empty)
    rule_id: str  # LanguageTool rule identifier
    category: str  # Category (e.g., "TYPOS", "GRAMMAR", "STYLE")
    context: str  # Text around the issue for display


class GrammarCheckResult(BaseModel):
    """Result of a grammar check."""

    issues: List[GrammarIssue]
    text_length: int
    issue_count: int
    categories: dict  # Count by category


def _get_tool():
    """Lazy initialization of LanguageTool."""
    global _language_tool, _tool_initialized, _init_error

    if _tool_initialized:
        if _init_error:
            raise _init_error
        return _language_tool

    _tool_initialized = True

    try:
        import language_tool_python
        logger.info("Initializing LanguageTool (this may take a moment on first run)...")
        _language_tool = language_tool_python.LanguageTool('en-US')
        logger.info("LanguageTool initialized successfully")
        return _language_tool
    except Exception as e:
        _init_error = RuntimeError(f"Failed to initialize LanguageTool: {str(e)}")
        logger.error(f"LanguageTool initialization failed: {e}")
        raise _init_error


class GrammarService:
    """Service for grammar and style checking."""

    # Categories to ignore (too noisy for creative writing)
    IGNORED_CATEGORIES = {
        "CASING",  # "The word 'the' should start with uppercase"
        "REDUNDANCY",  # Often intentional in prose
    }

    # Rules to ignore (too strict for fiction)
    IGNORED_RULES = {
        "UPPERCASE_SENTENCE_START",  # Allows sentences starting with lowercase
        "EN_QUOTES",  # Don't enforce quote style
        "MORFOLOGIK_RULE_EN_US",  # Catches many fantasy names
        "COMMA_PARENTHESIS_WHITESPACE",  # Too picky
        "WHITESPACE_RULE",  # Multiple spaces are fine in prose
    }

    def __init__(self):
        """Initialize grammar service."""
        self._tool = None

    @property
    def tool(self):
        """Get LanguageTool instance (lazy init)."""
        if self._tool is None:
            self._tool = _get_tool()
        return self._tool

    def is_available(self) -> bool:
        """Check if LanguageTool is available."""
        try:
            _ = self.tool
            return True
        except Exception:
            return False

    def check_text(self, text: str, enable_all_rules: bool = False) -> GrammarCheckResult:
        """
        Check text for grammar and style issues.

        Args:
            text: The prose text to check
            enable_all_rules: If True, don't filter out noisy rules

        Returns:
            GrammarCheckResult with all found issues
        """
        tool = self.tool
        matches = tool.check(text)

        issues = []
        category_counts = {}

        for match in matches:
            # Skip ignored categories/rules unless all rules enabled
            if not enable_all_rules:
                if match.category in self.IGNORED_CATEGORIES:
                    continue
                if match.ruleId in self.IGNORED_RULES:
                    continue

            # Extract context (50 chars before and after)
            start = max(0, match.offset - 50)
            end = min(len(text), match.offset + match.errorLength + 50)
            context = text[start:end]
            if start > 0:
                context = "..." + context
            if end < len(text):
                context = context + "..."

            issue = GrammarIssue(
                message=match.message,
                short_message=match.shortMessage or match.message[:50],
                offset=match.offset,
                length=match.errorLength,
                replacements=match.replacements[:5],  # Limit to 5 suggestions
                rule_id=match.ruleId,
                category=match.category,
                context=context
            )
            issues.append(issue)

            # Count by category
            category_counts[match.category] = category_counts.get(match.category, 0) + 1

        return GrammarCheckResult(
            issues=issues,
            text_length=len(text),
            issue_count=len(issues),
            categories=category_counts
        )


# Singleton instance
_grammar_service: Optional[GrammarService] = None


def get_grammar_service() -> GrammarService:
    """Get the singleton grammar service instance."""
    global _grammar_service
    if _grammar_service is None:
        _grammar_service = GrammarService()
    return _grammar_service
