import subprocess
import os
from typing import Any

from skills.base import BaseSkill, SkillResult, Capability
from infrastructure.security import confirm_action
from config.logger import logger


def _git(args: list[str], cwd: str | None = None, timeout: int = 15) -> tuple[int, str, str]:
    """Run a git command. Returns (returncode, stdout, stderr)."""
    try:
        res = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, timeout=timeout,
            cwd=cwd,
        )
        return res.returncode, res.stdout, res.stderr
    except FileNotFoundError:
        return 127, "", "git is not installed"
    except Exception as e:
        return 1, "", str(e)


def _find_repo_root(start: str | None = None) -> str:
    """Walk up from cwd to find the git repo root."""
    cwd = start or os.getcwd()
    code, out, _ = _git(["rev-parse", "--show-toplevel"], cwd=cwd)
    if code == 0:
        return out.strip()
    return cwd


class GitSkill(BaseSkill):
    """
    Developer-mode Git skill. Reads (branch/status/diff/log) are deterministic
    and instant. Any repo-MODIFYING action (commit/checkout/reset) requires confirmation.
    """

    name = "GIT"
    description = "Git status, branch, diff, log, and safe repo operations."
    permissions = ["READ_GIT", "CONFIRM_REQUIRED"]
    capability = Capability(
        name="git",
        description="Git repository status, branch, diff, log, commits, checkouts",
        supports=["git", "branch", "commit", "diff", "status", "repo"],
        requires_confirmation=False,
        deterministic=True,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        # Derive the action from the intent name (GIT_LOG -> log, GIT_DIFF -> diff, ...)
        # so the router's intent maps directly to the right git operation.
        intent = ""
        if context is not None:
            intent = (context.conversation_state or {}).get("intent", "")
        action = args.get("action") or {
            "GIT_STATUS": "status",
            "GIT_BRANCH": "branch",
            "GIT_DIFF": "diff",
            "GIT_LOG": "log",
            "GIT_COMMIT": "commit",
            "GIT_CHECKOUT": "checkout",
        }.get(intent, "status")

        repo = args.get("repo") or _find_repo_root()
        cwd = repo if os.path.isdir(repo) else None

        if action == "status":
            return self._status(cwd)
        if action == "branch":
            return self._branch(cwd)
        if action == "diff":
            return self._diff(cwd, args.get("path"))
        if action == "log":
            return self._log(cwd, args.get("limit", 10))
        if action == "commit":
            return self._commit(cwd, args.get("message", ""))
        if action == "checkout":
            return self._checkout(cwd, args.get("branch", ""))
        return SkillResult(success=False, message=f"Unknown git action '{action}'.", use_llm=False)

    def _status(self, cwd: str | None) -> SkillResult:
        code, out, err = _git(["status", "--short", "--branch"], cwd=cwd)
        if code != 0:
            return SkillResult(success=False, message=f"git status failed: {err.strip()}", use_llm=False)
        lines = out.strip().splitlines()
        branch = ""
        changes: list[str] = []
        for line in lines:
            if line.startswith("## "):
                branch = line[3:].strip()
            elif line.strip():
                changes.append(line.strip())
        msg = f"On branch: {branch}"
        if changes:
            msg += f"\n{len(changes)} changed item(s):\n" + "\n".join(f"  {c}" for c in changes[:20])
            if len(changes) > 20:
                msg += f"\n  … and {len(changes) - 20} more"
        else:
            msg += "\nWorking tree clean."
        return SkillResult(success=True, message=msg, data={"branch": branch, "changes": changes}, use_llm=False)

    def _branch(self, cwd: str | None) -> SkillResult:
        code, out, err = _git(["branch", "-a"], cwd=cwd)
        if code != 0:
            return SkillResult(success=False, message=f"git branch failed: {err.strip()}", use_llm=False)
        return SkillResult(success=True, message="Branches:\n" + out.strip(), data={"branches": out.splitlines()}, use_llm=False)

    def _diff(self, cwd: str | None, path: str | None) -> SkillResult:
        args = ["diff", "--stat"]
        if path:
            args.append("--")
            args.append(path)
        code, out, err = _git(args, cwd=cwd)
        if code != 0:
            return SkillResult(success=False, message=f"git diff failed: {err.strip()}", use_llm=False)
        if not out.strip():
            return SkillResult(success=True, message="No uncommitted changes.", data={"diff": ""}, use_llm=False)
        return SkillResult(success=True, message="Changes:\n" + out.strip(), data={"diff": out.strip()}, use_llm=False)

    def _log(self, cwd: str | None, limit: int) -> SkillResult:
        code, out, err = _git(["log", "--oneline", "-n", str(limit)], cwd=cwd)
        if code != 0:
            return SkillResult(success=False, message=f"git log failed: {err.strip()}", use_llm=False)
        return SkillResult(success=True, message=f"Recent commits (last {limit}):\n" + out.strip(), data={"log": out.splitlines()}, use_llm=False)

    def _commit(self, cwd: str | None, message: str) -> SkillResult:
        if not message:
            return SkillResult(success=False, message="No commit message provided. Usage: commit with message '...'", use_llm=False)
        if not confirm_action(f"git commit -m \"{message}\""):
            return SkillResult(success=False, message="Cancelled — commit was not created.", use_llm=False)
        code, out, err = _git(["commit", "-m", message], cwd=cwd)
        if code != 0:
            return SkillResult(success=False, message=f"git commit failed: {err.strip()}", use_llm=False)
        return SkillResult(success=True, message=f"Committed:\n{out.strip()}", use_llm=False)

    def _checkout(self, cwd: str | None, branch: str) -> SkillResult:
        if not branch:
            return SkillResult(success=False, message="No branch specified. Usage: checkout branch '...'", use_llm=False)
        if not confirm_action(f"git checkout {branch}"):
            return SkillResult(success=False, message="Cancelled — checkout was not performed.", use_llm=False)
        code, out, err = _git(["checkout", branch], cwd=cwd)
        if code != 0:
            return SkillResult(success=False, message=f"git checkout failed: {err.strip()}", use_llm=False)
        return SkillResult(success=True, message=f"Switched to branch '{branch}':\n{out.strip()}", use_llm=False)
