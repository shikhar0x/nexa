from typing import Any
from skills.base import BaseSkill, SkillResult
from memory.service import MemoryService
from infrastructure.security import confirm_action


class MemorySkill(BaseSkill):
    """
    Skill for deterministic memory operations:
    statistics, listing, vector searching, exporting, deleting matching memories,
    confirmation-gated clearing, and summarization retrieval.
    """

    name = "MEMORY"
    description = "Handles deterministic database memory queries and operations."
    permissions = ["READ_MEMORY", "WRITE_MEMORY"]

    def __init__(self, memory_service: MemoryService | None = None) -> None:
        self.memory_service = memory_service or MemoryService()

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        intent = context.conversation_state.get("intent", "MEMORY_STATS")

        if intent == "MEMORY_STATS":
            return self._handle_stats()
        elif intent == "MEMORY_LIST":
            return self._handle_list()
        elif intent == "MEMORY_SEARCH":
            return self._handle_search(args.get("query", ""))
        elif intent == "MEMORY_EXPORT":
            return self._handle_export()
        elif intent == "MEMORY_DELETE":
            return self._handle_delete(args.get("query", ""))
        elif intent == "MEMORY_CLEAR":
            return self._handle_clear()
        elif intent == "MEMORY_SUMMARIZE":
            return self._handle_summarize(args.get("query", ""), context)
        else:
            return self._handle_stats()

    def _handle_stats(self) -> SkillResult:
        stats = self.memory_service.get_memory_stats()
        message = (
            "Memory Summary:\n"
            f"• Total messages logged: {stats['total_messages']}\n"
            f"• User prompts: {stats['user_messages']}\n"
            f"• Assistant responses: {stats['assistant_messages']}\n"
            f"• Vector memories embedded: {stats['vector_memories']}\n"
            f"• Oldest conversation: {stats['oldest_date']}\n"
            f"• Latest conversation: {stats['latest_date']}"
        )
        return SkillResult(
            success=True,
            data=stats,
            message=message,
            use_llm=False,  # Deterministic fact query bypasses LLM
        )

    def _handle_list(self) -> SkillResult:
        recent = self.memory_service.list_recent_memories(limit=10)
        if not recent:
            return SkillResult(
                success=True,
                message="Memory is currently empty — no conversations logged.",
                data={"memories": []},
                use_llm=False,
            )

        lines = ["Recent logged memories:\n"]
        for m in recent:
            lines.append(f"• [ID #{m['id']}] {m['role'].capitalize()} ({m['timestamp'].split('T')[0]}): {m['content']}")

        return SkillResult(
            success=True,
            data={"memories": recent},
            message="\n".join(lines),
            use_llm=False,  # Factual list bypasses LLM
        )

    def _handle_search(self, query: str) -> SkillResult:
        if not query:
            return SkillResult(
                success=False,
                message="No memory search query provided.",
                use_llm=False,
            )

        results = self.memory_service.search_memories(query, top_k=5)
        if not results:
            return SkillResult(
                success=True,
                message=f"No memories found matching '{query}'.",
                data={"query": query, "results": []},
                use_llm=False,
            )

        lines = [f"Memory search results for '{query}':\n"]
        for r in results:
            lines.append(f"• {r}")

        return SkillResult(
            success=True,
            data={"query": query, "results": results},
            message="\n".join(lines),
            use_llm=False,  # Factual search results bypass LLM
        )

    def _handle_export(self) -> SkillResult:
        export_path = self.memory_service.export_conversations("nexa_memory_export.md")
        return SkillResult(
            success=True,
            data={"export_path": export_path},
            message=f"Exported all conversations to: {export_path}",
            use_llm=False,  # Export confirmation bypasses LLM
        )

    def _handle_delete(self, query: str) -> SkillResult:
        if not query:
            return SkillResult(
                success=False,
                message="No search term provided for memory deletion.",
                use_llm=False,
            )

        count = self.memory_service.delete_matching_memories(query)
        if count == 0:
            return SkillResult(
                success=True,
                message=f"No matching memories found to delete for term '{query}'.",
                data={"deleted_count": 0},
                use_llm=False,
            )

        return SkillResult(
            success=True,
            data={"deleted_count": count, "query": query},
            message=f"Deleted {count} memory record(s) matching '{query}'.",
            use_llm=False,  # Deletion confirmation bypasses LLM
        )

    def _handle_clear(self) -> SkillResult:
        if not confirm_action("clear all persistent conversation and vector memory"):
            return SkillResult(
                success=False,
                message="Cancelled — memory clear operation was aborted.",
                data={"status": "cancelled"},
                use_llm=False,
            )

        self.memory_service.clear_all_memory()
        return SkillResult(
            success=True,
            message="Memory reset successfully. All conversation logs and vector stores wiped.",
            data={"status": "cleared"},
            use_llm=False,  # Reset confirmation bypasses LLM
        )

    def _handle_summarize(self, query: str, context: Any) -> SkillResult:
        search_query = query if query else context.user_input
        results = self.memory_service.search_memories(search_query, top_k=10)
        formatted_results = "\n".join(f"- {r}" for r in results) if results else "No specific context found."

        return SkillResult(
            success=True,
            data={"query": search_query, "retrieved": results},
            message=f"Retrieved Context for Summarization:\n{formatted_results}",
            use_llm=True,  # Summarization query uses LLM reasoning!
        )
