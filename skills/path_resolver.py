from pathlib import Path

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


def resolve_path(raw_path: str) -> Path:
    """
    Resolves a raw input string, relative path, or special folder name (e.g. 'Downloads')
    into an absolute Path object.
    """
    if not raw_path:
        return Path.cwd()

    cleaned = raw_path.strip().strip("'\"")
    cleaned_lower = cleaned.lower().rstrip("/")

    # Check direct special folders lookup
    if cleaned_lower in SPECIAL_FOLDERS:
        return SPECIAL_FOLDERS[cleaned_lower]

    if cleaned.startswith("home/"):
        cleaned = "/" + cleaned

    path_obj = Path(cleaned).expanduser()

    # If non-absolute, check if leading directory component is a special folder
    if not path_obj.is_absolute() and path_obj.parts:
        first_part = path_obj.parts[0].lower()
        if first_part in SPECIAL_FOLDERS:
            base = SPECIAL_FOLDERS[first_part]
            rest = Path(*path_obj.parts[1:]) if len(path_obj.parts) > 1 else Path()
            return base / rest

    return path_obj
