import os
import re
import time
from pathlib import Path
from typing import Any, Optional
from config.settings import settings

SPECIAL_FOLDERS: dict[str, Path] = {
    "downloads": Path.home() / "Downloads",
    "desktop": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "pictures": Path.home() / "Pictures",
    "music": Path.home() / "Music",
    "videos": Path.home() / "Videos",
    "templates": Path.home() / "Templates",
    "public": Path.home() / "Public",
    "home": Path.home(),
}


def expand_special_folder(raw_name: str) -> Optional[Path]:
    """
    Looks up a special folder name case-insensitively.
    Strips leading 'my ', 'the ', etc., and trailing 'folder' or 'directory' suffixes.
    """
    if not raw_name:
        return None

    cleaned = raw_name.strip().strip("'\"").lower()
    cleaned = re.sub(r"^(?:my|the|in\s+my|inside\s+my|in\s+the|inside\s+the)\s+", "", cleaned).strip()
    cleaned = re.sub(r"\s+(folder|directory)$", "", cleaned).strip()

    return SPECIAL_FOLDERS.get(cleaned)


def normalize_directory(path: Path | str) -> Path:
    """
    Normalizes a directory path, ensuring tilde expansion and absolute path resolution.
    """
    if isinstance(path, str):
        path = Path(path.strip().strip("'\""))
    return path.expanduser().resolve()


def validate_exists(path: Path | str) -> bool:
    """
    Validates whether a path exists on the filesystem.
    Never silently converts non-existent paths into existing paths.
    """
    if isinstance(path, str):
        if not path.strip():
            return False
        path = Path(path.strip().strip("'\"")).expanduser()
    return path.exists()


def expand_relative_path(raw_path: str, working_dir: Optional[Path] = None) -> Path:
    """
    Expands a relative path against an explicit working directory (default: Path.cwd()).
    Resolves leading special folder components if present.
    """
    if not raw_path:
        return working_dir or Path.cwd()

    cleaned = raw_path.strip().strip("'\"")
    if cleaned.startswith("home/"):
        cleaned = "/" + cleaned

    path_obj = Path(cleaned).expanduser()
    if path_obj.is_absolute():
        return path_obj

    # Check if leading part is a special folder
    if path_obj.parts:
        first_part = path_obj.parts[0].lower()
        special_base = expand_special_folder(first_part)
        if special_base:
            rest = Path(*path_obj.parts[1:]) if len(path_obj.parts) > 1 else Path()
            return special_base / rest

    base = working_dir or Path.cwd()
    return base / path_obj


def resolve_path(raw_path: str) -> Path:
    """
    Resolves a raw input string, relative path, or special folder name (e.g. 'Downloads')
    into an absolute Path object.
    """
    if not raw_path:
        return Path.cwd()

    cleaned = raw_path.strip().strip("'\"")
    cleaned_lower = cleaned.lower().rstrip("/")

    # Relative/special phrase checks
    if cleaned_lower in ("current", "current directory", "current folder", "this directory", "here"):
        return Path.cwd()

    if cleaned_lower in ("parent", "parent directory", "parent folder", "up"):
        return Path.cwd().parent

    # Check direct special folders lookup
    special_folder = expand_special_folder(cleaned_lower)
    if special_folder:
        return special_folder

    if cleaned.startswith("home/"):
        cleaned = "/" + cleaned

    path_obj = Path(cleaned).expanduser()

    # If non-absolute, check if leading directory component is a special folder
    if not path_obj.is_absolute() and path_obj.parts:
        first_part = path_obj.parts[0].lower()
        special_base = expand_special_folder(first_part)
        if special_base:
            rest = Path(*path_obj.parts[1:]) if len(path_obj.parts) > 1 else Path()
            return special_base / rest

    return path_obj.resolve() if path_obj.is_absolute() else path_obj


def expand_filename(
    raw_path: str,
    context: Any = None,
    backend: Any = None,
    search_dirs: Optional[list[Path]] = None,
) -> tuple[str, Any]:
    """
    Alias for resolve_filename_or_path providing filename expansion across search priorities.
    """
    return resolve_filename_or_path(raw_path, context=context, backend=backend, search_dirs=search_dirs)


def set_active_directory(context: Any, dir_path: Path | str) -> None:
    """
    Centralized helper recording successful working directory and timestamp into workspace_state.
    """
    if not context or not hasattr(context, "workspace_state"):
        return
    norm_path = str(resolve_path(str(dir_path)))
    context.workspace_state["active_directory"] = norm_path
    context.workspace_state["active_directory_timestamp"] = time.time()


def get_active_directory(context: Any) -> Optional[Path]:
    """
    Retrieves active working directory from context if valid and not expired according to working_directory_timeout.
    """
    if not context or not hasattr(context, "workspace_state"):
        return None

    workspace_state = context.workspace_state
    if not isinstance(workspace_state, dict):
        return None

    active_dir = workspace_state.get("active_directory")
    timestamp = workspace_state.get("active_directory_timestamp")

    if not active_dir:
        return None

    if timestamp is not None:
        elapsed = time.time() - float(timestamp)
        if elapsed > settings.working_directory_timeout:
            return None

    path_obj = resolve_path(str(active_dir))
    if validate_exists(path_obj) and path_obj.is_dir():
        return path_obj

    return None


def resolve_filename_or_path(
    raw_path: str,
    context: Any = None,
    backend: Any = None,
    search_dirs: Optional[list[Path]] = None,
) -> tuple[str, Any]:
    """
    Resolves an explicit path, or performs deterministic filename search if raw_path is filename-only.

    Search priority:
      1. Explicit existing file/directory path
      2. Active filesystem directory from context.workspace_state["active_directory"] (if not expired)
      3. Known folders (Desktop, Documents, Downloads) / search_dirs
      4. Home directory (if needed)

    Returns:
      ("EXACT", resolved_Path_obj)
      ("NOT_FOUND", raw_path)
      ("MULTIPLE", list_of_matching_path_strings)
    """
    if not raw_path:
        return ("NOT_FOUND", raw_path)

    # 1. First check if raw_path resolves directly to an existing path on disk
    resolved = resolve_path(raw_path)
    if validate_exists(resolved):
        return ("EXACT", resolved)

    # 2. Check if raw_path has path separators or parent component (/foo/bar, ./bar, ~/foo)
    cleaned = raw_path.strip().strip("'\"")
    path_obj = Path(cleaned).expanduser()

    # If explicit path with directory structure does not exist, return NOT_FOUND directly
    if path_obj.is_absolute() or len(path_obj.parts) > 1:
        return ("NOT_FOUND", cleaned)

    # 3. Handle filename-only search
    filename = path_obj.name
    matches: list[str] = []

    # Priority 1: Explicit single search_dirs hint (e.g. explicit 'from Documents' hint)
    if search_dirs is not None and len(search_dirs) == 1:
        s_dir = search_dirs[0]
        if validate_exists(s_dir) and s_dir.is_dir():
            for p in s_dir.rglob(filename):
                if p.is_file() and str(p) not in matches and p.name.lower() == filename.lower():
                    matches.append(str(p))
        if len(matches) == 1:
            return ("EXACT", Path(matches[0]))
        elif len(matches) > 1:
            return ("MULTIPLE", matches)

    # Priority 2: Active working directory from context (if valid and unexpired)
    active_path = get_active_directory(context)

    if active_path:
        for p in active_path.rglob(filename):
            if p.is_file() and str(p) not in matches and p.name.lower() == filename.lower():
                matches.append(str(p))

        if len(matches) == 1:
            return ("EXACT", Path(matches[0]))
        elif len(matches) > 1:
            return ("MULTIPLE", matches)

    # Priority 3: Search specified search_dirs or backend known folders
    if search_dirs is not None:
        for s_dir in search_dirs:
            if validate_exists(s_dir) and s_dir.is_dir():
                for p in s_dir.rglob(filename):
                    if p.is_file() and str(p) not in matches and p.name.lower() == filename.lower():
                        matches.append(str(p))
    else:
        if backend is None:
            from infrastructure.search.oswalk import OsWalkSearchBackend
            backend = OsWalkSearchBackend()
        search_matches = backend.search_filenames(filename)
        for m in search_matches:
            if Path(m).name.lower() == filename.lower():
                if m not in matches:
                    matches.append(m)

    if not matches:
        return ("NOT_FOUND", filename)
    elif len(matches) == 1:
        return ("EXACT", Path(matches[0]))
    else:
        return ("MULTIPLE", matches)


def fuzzy_suggest_directory(
    raw_input: str,
    context: Any = None,
    custom_candidates: Optional[list[str]] = None,
) -> list[str]:
    """
    Deterministically suggests existing directory names for invalid or misspelled input.

    Candidate sources:
      1. Known special folders (Downloads, Desktop, Documents, etc.)
      2. Subdirectories in active working directory (from context)
      3. Subdirectories in current working directory (Path.cwd())
      4. Explicit custom candidates (if provided in test environments)

    Uses difflib.get_close_matches with a conservative cutoff (0.6).
    Never hallucinates or executes suggestions automatically.
    """
    import difflib

    if not raw_input or not raw_input.strip():
        return []

    cleaned = raw_input.strip().strip("'\"")
    input_name = Path(cleaned).name.strip()
    if not input_name:
        return []

    candidate_map: dict[str, str] = {}

    # 1. Known special folders
    for key, path in SPECIAL_FOLDERS.items():
        canonical_name = path.name
        candidate_map[key] = canonical_name
        candidate_map[canonical_name.lower()] = canonical_name

    # 2. Custom candidates override (useful in isolated test environments)
    if custom_candidates:
        for cand in custom_candidates:
            cand_name = Path(cand).name
            candidate_map[cand_name.lower()] = cand_name

    # 3. Subdirectories in active directory
    active_dir = get_active_directory(context)
    if active_dir:
        try:
            for item in active_dir.iterdir():
                if item.is_dir():
                    candidate_map[item.name.lower()] = item.name
        except Exception:
            pass

    # 4. Subdirectories in current working directory
    try:
        for item in Path.cwd().iterdir():
            if item.is_dir() and not item.name.startswith("."):
                candidate_map[item.name.lower()] = item.name
    except Exception:
        pass

    # Match close names
    match_keys = difflib.get_close_matches(input_name.lower(), list(candidate_map.keys()), n=3, cutoff=0.6)

    results: list[str] = []
    for mk in match_keys:
        canonical = candidate_map[mk]
        if canonical not in results:
            results.append(canonical)

    return results

