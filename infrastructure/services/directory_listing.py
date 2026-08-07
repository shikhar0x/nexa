import os
from pathlib import Path
from skills.schemas import DirectoryListingData, DirectoryItem


class DirectoryListingService:
    """Service scanning and retrieving real file/folder contents of a directory."""

    def list_directory(self, target_path: str = "") -> DirectoryListingData:
        if not target_path or target_path.lower() in ("active_file", "workspace"):
            path_obj = Path.cwd()
        else:
            cleaned = target_path.strip().strip("'\"")
            if cleaned.startswith("home/"):
                cleaned = "/" + cleaned
            path_obj = Path(os.path.expanduser(cleaned))

        if not path_obj.exists():
            raise FileNotFoundError(f"Path '{path_obj}' does not exist.")

        if not path_obj.is_dir():
            raise NotADirectoryError(f"Path '{path_obj}' is a file, not a directory.")

        files = []
        directories = []

        with os.scandir(path_obj) as entries:
            for entry in entries:
                try:
                    stat = entry.stat()
                    item = DirectoryItem(
                        name=entry.name,
                        path=entry.path,
                        is_dir=entry.is_dir(),
                        size_bytes=stat.st_size if not entry.is_dir() else 0,
                        extension=Path(entry.name).suffix.lower() if not entry.is_dir() else "",
                    )
                    if entry.is_dir():
                        directories.append(item)
                    else:
                        files.append(item)
                except OSError:
                    pass

        files.sort(key=lambda x: x.name.lower())
        directories.sort(key=lambda x: x.name.lower())

        return DirectoryListingData(
            target_path=str(path_obj.resolve()),
            total_items=len(files) + len(directories),
            total_files=len(files),
            total_directories=len(directories),
            files=files,
            directories=directories,
        )
