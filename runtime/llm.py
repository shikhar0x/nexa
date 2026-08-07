from typing import Iterator
import ollama

from runtime.context import ConversationContext
from config.settings import settings
from config.constants import SYSTEM_PROMPT, GROUNDED_INTERPRETATION_PROMPT
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
        )

        for chunk in response_stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content

    def generate(self, context: ConversationContext) -> str:
        """Non-streaming fallback method returning accumulated full response string."""
        return "".join(self.stream(context))

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

