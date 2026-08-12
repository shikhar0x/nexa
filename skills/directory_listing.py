import time
from dataclasses import asdict
from typing import Any
from skills.base import BaseSkill, SkillResult, Capability, PendingAction
from infrastructure.services.directory_listing import DirectoryListingService


class DirectoryListingSkill(BaseSkill):
    """Presentation skill wrapper for scanning and listing directory contents."""

    name = "DIRECTORY_LISTING"
    description = "Scans directory contents (e.g. Downloads, Desktop, workspace) for natural AI summaries."
    permissions = ["READ_FILES"]
    capability = Capability(
        name="directory_listing",
        description="Scans directory contents and lists files, subdirectories, and file counts",
        supports=["directory_listing", "ls", "list_files", "folder_contents"],
        requires_confirmation=False,
        deterministic=True,
    )

    def __init__(self, service: DirectoryListingService | None = None) -> None:
        self.service = service or DirectoryListingService()

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        target_path = args.get("path", "").strip().strip("'\"")

        if target_path in ("this_folder", "that_folder"):
            active_dir = getattr(context, "workspace_state", {}).get("active_directory") if context else None
            if active_dir:
                target_path = active_dir
            else:
                return SkillResult(
                    success=False,
                    message="Which folder would you like to list?",
                    use_llm=False,
                    pending_action=PendingAction(
                        skill_name=self.name,
                        args=dict(args),
                        missing_args=["path"],
                        prompt="Which folder would you like to list?",
                        timestamp=time.time(),
                    ),
                )

        if not target_path or (args.get("ask_folder") and not target_path):
            return SkillResult(
                success=False,
                message="Which folder would you like to list?",
                use_llm=False,
                pending_action=PendingAction(
                    skill_name=self.name,
                    args=dict(args),
                    missing_args=["path"],
                    prompt="Which folder would you like to list?",
                    timestamp=time.time(),
                ),
            )

        try:
            listing_data = self.service.list_directory(target_path)
        except Exception as e:
            from skills.path_resolver import fuzzy_suggest_directory
            suggestions = fuzzy_suggest_directory(target_path, context=context)
            if suggestions:
                sug_str = "', '".join(suggestions)
                message = f"Could not list directory '{target_path}': Path does not exist. Did you mean '{sug_str}'?"
            else:
                message = f"Could not list directory contents: {e}"

            return SkillResult(
                success=False,
                message=message,
                data={"error": "not_found", "attempted_path": target_path, "suggestions": suggestions},
                use_llm=False,
            )

        data_dict = asdict(listing_data)

        # Update active working directory context
        from skills.path_resolver import set_active_directory
        set_active_directory(context, listing_data.target_path)

        dir_sample = [f"  - 📁 {d.name}/" for d in listing_data.directories[:10]]
        file_sample = [f"  - 📄 {f.name} ({round(f.size_bytes / 1024, 1)} KB)" for f in listing_data.files[:15]]

        message_lines = [
            f"Directory Contents of '{listing_data.target_path}' ({listing_data.total_items} items total: {listing_data.total_directories} folders, {listing_data.total_files} files):\n"
        ]
        if dir_sample:
            message_lines.append("Subdirectories:")
            message_lines.extend(dir_sample)
        if file_sample:
            message_lines.append("\nFiles:")
            message_lines.extend(file_sample)

        message = "\n".join(message_lines)

        return SkillResult(
            success=True,
            data=data_dict,
            message=message,
            use_llm=True,
            allow_interpretation=True,
        )
