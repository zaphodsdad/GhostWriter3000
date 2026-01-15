"""LLM API integration service (supports Anthropic direct and OpenRouter)."""

import asyncio
from typing import Optional, Dict, Any
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from app.config import settings
from app.api.routes.settings import get_api_key, load_user_settings


class LLMService:
    """Service for interacting with LLM APIs (Anthropic or OpenRouter)."""

    def __init__(self):
        """Initialize LLM API client based on provider setting."""
        self.provider = settings.llm_provider
        self.semaphore = asyncio.Semaphore(3)  # Max 3 concurrent API calls
        self._current_api_key = None
        self._init_client()

    def _init_client(self):
        """Initialize or reinitialize the API client."""
        if self.provider == "anthropic":
            api_key = get_api_key("anthropic_api_key")
            self._current_api_key = api_key
            self.client = AsyncAnthropic(api_key=api_key or "placeholder")
        elif self.provider == "openrouter":
            api_key = get_api_key("openrouter_api_key")
            self._current_api_key = api_key
            self.client = AsyncOpenAI(
                api_key=api_key or "placeholder",
                base_url="https://openrouter.ai/api/v1"
            )
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    def _check_and_refresh_client(self):
        """Check if API key changed and refresh client if needed."""
        key_name = "anthropic_api_key" if self.provider == "anthropic" else "openrouter_api_key"
        current_key = get_api_key(key_name)
        if current_key != self._current_api_key:
            self._init_client()

    async def generate_prose(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Generate prose using LLM API.

        Args:
            system_prompt: System prompt with context
            user_prompt: User prompt with scene outline
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            model: Optional model override (uses settings.generation_model if None)

        Returns:
            Generated prose text

        Raises:
            Exception: If API call fails
        """
        self._check_and_refresh_client()
        async with self.semaphore:
            try:
                if self.provider == "anthropic":
                    return await self._generate_anthropic(
                        system_prompt, user_prompt, temperature, max_tokens, model
                    )
                else:  # openrouter
                    return await self._generate_openrouter(
                        system_prompt, user_prompt, temperature, max_tokens, model
                    )
            except Exception as e:
                raise Exception(f"LLM API generation failed: {str(e)}")

    async def _generate_anthropic(
        self, system_prompt: str, user_prompt: str,
        temperature: Optional[float], max_tokens: Optional[int],
        model: Optional[str] = None
    ) -> str:
        """Generate using Anthropic API."""
        response = await self.client.messages.create(
            model=model or settings.generation_model,
            max_tokens=max_tokens or settings.generation_max_tokens,
            temperature=temperature or settings.generation_temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text

    async def _generate_openrouter(
        self, system_prompt: str, user_prompt: str,
        temperature: Optional[float], max_tokens: Optional[int],
        model: Optional[str] = None
    ) -> str:
        """Generate using OpenRouter API."""
        response = await self.client.chat.completions.create(
            model=model or settings.generation_model,
            max_tokens=max_tokens or settings.generation_max_tokens,
            temperature=temperature or settings.generation_temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content

    async def critique_prose(
        self,
        prose: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        style_guide: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate critique of prose using LLM API.

        Args:
            prose: Prose text to critique
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            model: Optional model override (uses settings.critique_model if None)
            style_guide: Optional style guide to critique against

        Returns:
            Critique text

        Raises:
            Exception: If API call fails
        """
        self._check_and_refresh_client()
        async with self.semaphore:
            try:
                from app.utils.prompt_templates import build_critique_prompt

                system_prompt = "You are a skilled literary critic who provides constructive feedback on narrative prose."
                if style_guide and style_guide.get('guide'):
                    system_prompt += " Pay special attention to whether the prose follows the provided style guide."
                user_prompt = build_critique_prompt(prose, style_guide)
                use_model = model or settings.critique_model

                if self.provider == "anthropic":
                    response = await self.client.messages.create(
                        model=use_model,
                        max_tokens=max_tokens or settings.critique_max_tokens,
                        temperature=temperature or settings.critique_temperature,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    return response.content[0].text
                else:  # openrouter
                    response = await self.client.chat.completions.create(
                        model=use_model,
                        max_tokens=max_tokens or settings.critique_max_tokens,
                        temperature=temperature or settings.critique_temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    return response.choices[0].message.content

            except Exception as e:
                raise Exception(f"LLM API critique failed: {str(e)}")

    async def critique_prose_polish(
        self,
        prose: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        style_guide: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate polish-mode critique (line edits, not structural).

        Args:
            prose: Prose text to critique
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            model: Optional model override (uses settings.critique_model if None)
            style_guide: Optional style guide to critique against

        Returns:
            Polish critique text

        Raises:
            Exception: If API call fails
        """
        self._check_and_refresh_client()
        async with self.semaphore:
            try:
                from app.utils.prompt_templates import build_polish_critique_prompt

                system_prompt = "You are a skilled copy editor who focuses on line-level refinements: word choice, rhythm, and clarity. You do NOT suggest structural changes."
                user_prompt = build_polish_critique_prompt(prose, style_guide)
                use_model = model or settings.critique_model

                if self.provider == "anthropic":
                    response = await self.client.messages.create(
                        model=use_model,
                        max_tokens=max_tokens or settings.critique_max_tokens,
                        temperature=temperature or settings.critique_temperature,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    return response.content[0].text
                else:  # openrouter
                    response = await self.client.chat.completions.create(
                        model=use_model,
                        max_tokens=max_tokens or settings.critique_max_tokens,
                        temperature=temperature or settings.critique_temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    return response.choices[0].message.content

            except Exception as e:
                raise Exception(f"LLM API polish critique failed: {str(e)}")

    async def revise_prose(
        self,
        original_prose: str,
        critique: str,
        system_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        instructions: Optional[str] = None
    ) -> str:
        """
        Revise prose based on critique using LLM API.

        Args:
            original_prose: Original prose text
            critique: Critique of the prose
            system_prompt: System prompt with context
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            model: Optional model override (uses settings.generation_model if None)
            instructions: Optional user-provided guidance for the revision

        Returns:
            Revised prose text

        Raises:
            Exception: If API call fails
        """
        self._check_and_refresh_client()
        async with self.semaphore:
            try:
                from app.utils.prompt_templates import build_revision_prompt

                user_prompt = build_revision_prompt(original_prose, critique, instructions)
                use_model = model or settings.generation_model

                if self.provider == "anthropic":
                    response = await self.client.messages.create(
                        model=use_model,
                        max_tokens=max_tokens or settings.generation_max_tokens,
                        temperature=temperature or settings.generation_temperature,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    return response.content[0].text
                else:  # openrouter
                    response = await self.client.chat.completions.create(
                        model=use_model,
                        max_tokens=max_tokens or settings.generation_max_tokens,
                        temperature=temperature or settings.generation_temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    return response.choices[0].message.content

            except Exception as e:
                raise Exception(f"LLM API revision failed: {str(e)}")

    async def revise_prose_polish(
        self,
        original_prose: str,
        critique: str,
        system_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        instructions: Optional[str] = None
    ) -> str:
        """
        Apply polish-mode revisions (minimal changes, preserve structure).

        Args:
            original_prose: Original prose text
            critique: Polish critique of the prose
            system_prompt: System prompt with context
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            model: Optional model override (uses settings.generation_model if None)
            instructions: Optional user-provided guidance for the revision

        Returns:
            Polished prose text

        Raises:
            Exception: If API call fails
        """
        self._check_and_refresh_client()
        async with self.semaphore:
            try:
                from app.utils.prompt_templates import build_polish_revision_prompt

                user_prompt = build_polish_revision_prompt(original_prose, critique, instructions)
                use_model = model or settings.generation_model

                if self.provider == "anthropic":
                    response = await self.client.messages.create(
                        model=use_model,
                        max_tokens=max_tokens or settings.generation_max_tokens,
                        temperature=temperature or settings.generation_temperature,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    return response.content[0].text
                else:  # openrouter
                    response = await self.client.chat.completions.create(
                        model=use_model,
                        max_tokens=max_tokens or settings.generation_max_tokens,
                        temperature=temperature or settings.generation_temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    return response.choices[0].message.content

            except Exception as e:
                raise Exception(f"LLM API polish revision failed: {str(e)}")

    async def revise_selection(
        self,
        full_prose: str,
        selection: str,
        selection_start: int,
        selection_end: int,
        system_prompt: str,
        critique: str = None,
        instructions: str = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Revise only a selected portion of prose.

        Args:
            full_prose: Complete prose text
            selection: Selected text to revise
            selection_start: Start index of selection
            selection_end: End index of selection
            system_prompt: System prompt with context
            critique: Optional critique context
            instructions: Optional user guidance
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            model: Optional model override

        Returns:
            Revised selection text only

        Raises:
            Exception: If API call fails
        """
        self._check_and_refresh_client()
        async with self.semaphore:
            try:
                from app.utils.prompt_templates import build_selection_revision_prompt

                user_prompt = build_selection_revision_prompt(
                    full_prose, selection, selection_start, selection_end, critique, instructions
                )
                use_model = model or settings.generation_model

                if self.provider == "anthropic":
                    response = await self.client.messages.create(
                        model=use_model,
                        max_tokens=max_tokens or settings.generation_max_tokens,
                        temperature=temperature or settings.generation_temperature,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    return response.content[0].text
                else:  # openrouter
                    response = await self.client.chat.completions.create(
                        model=use_model,
                        max_tokens=max_tokens or settings.generation_max_tokens,
                        temperature=temperature or settings.generation_temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    return response.choices[0].message.content

            except Exception as e:
                raise Exception(f"LLM API selection revision failed: {str(e)}")

    async def generate_summary(
        self,
        scene_title: str,
        prose: str,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate scene summary using LLM API.

        Args:
            scene_title: Title of the scene
            prose: Prose text to summarize
            max_tokens: Optional max tokens override

        Returns:
            Scene summary text

        Raises:
            Exception: If API call fails
        """
        self._check_and_refresh_client()
        async with self.semaphore:
            try:
                from app.utils.prompt_templates import build_summary_prompt

                system_prompt = "You are a continuity editor who creates concise scene summaries for long-form narrative projects."
                user_prompt = build_summary_prompt(scene_title, prose)

                if self.provider == "anthropic":
                    response = await self.client.messages.create(
                        model=settings.critique_model,
                        max_tokens=max_tokens or 1000,
                        temperature=0.3,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    return response.content[0].text
                else:  # openrouter
                    response = await self.client.chat.completions.create(
                        model=settings.critique_model,
                        max_tokens=max_tokens or 1000,
                        temperature=0.3,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    return response.choices[0].message.content

            except Exception as e:
                raise Exception(f"LLM API summary generation failed: {str(e)}")


# Global service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
