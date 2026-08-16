from typing import Iterator, Optional
import json
import re
import ollama

from runtime.context import ConversationContext
from config.settings import settings
from config.constants import SYSTEM_PROMPT, GROUNDED_INTERPRETATION_PROMPT, INTENT_CLASSIFICATION_PROMPT
from config.logger import logger


class LLMEngine:
    """LLM Interface accepting ConversationContext to generate and stream natural responses."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.llm_model

    def stream(self, context: ConversationContext) -> Iterator[str]:
        """
        Stream generated text chunks natively using Ollama's stream=True API.
        Yields individual string tokens as they arrive from Ollama.
        """
        prompt = self._build_prompt(context)
        logger.debug(f"Streaming prompt to Ollama model '{self.model_name}'...")

        messages = [{"role": "system", "content": prompt}]
        if context.recent_history:
            for item in context.recent_history:
                messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": context.user_input})

        response_stream = ollama.chat(
            model=self.model_name,
            messages=messages,
            stream=True,
            options={
                "temperature": settings.temperature,
                "num_ctx": settings.num_ctx,
            },
        )

        for chunk in response_stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content

    def generate(self, context: ConversationContext) -> str:
        """Non-streaming fallback method returning accumulated full response string."""
        return "".join(self.stream(context))

    def classify_intent(self, user_input: str) -> Optional[dict]:
        """
        Use the SAME local model to map an unclassified user message to one of
        Nexa's known intents. Returns {"intent": "<NAME>"} or None on any
        failure (Ollama down, invalid JSON, unexpected output). The caller is
        responsible for whitelisting the suggested intent.
        """
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT},
                    {"role": "user", "content": user_input},
                ],
                stream=False,
                format="json",
                options={
                    "temperature": 0.0,
                    "num_ctx": settings.num_ctx,
                    "num_predict": settings.classification_max_tokens,
                },
            )
            content = response.get("message", {}).get("content", "").strip()
            # Tolerate fenced JSON output from smaller models
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
            parsed = json.loads(content)
            if isinstance(parsed, dict) and isinstance(parsed.get("intent"), str):
                return parsed
            logger.debug(f"LLM classification returned unexpected shape: {parsed!r}")
        except Exception as exc:
            logger.debug(f"LLM intent classification failed, falling back to GENERAL: {exc}")
        return None

    def _build_prompt(self, context: ConversationContext) -> str:
        prompt = SYSTEM_PROMPT

        if context.skill_result and context.skill_result.allow_interpretation:
            prompt += f"\n\n{GROUNDED_INTERPRETATION_PROMPT}"

        if context.memory_context:
            prompt += f"\n\n{context.memory_context}"

        formatted_tool_data = context.format_for_llm()
        if formatted_tool_data:
            prompt += f"\n\n{formatted_tool_data}"

        return prompt

