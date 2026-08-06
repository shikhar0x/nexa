from typing import Iterator
import sys
import io


class ConsoleRenderer:
    """Renders responses to the console using live native token streaming or static output."""

    def render_stream(self, chunk_generator: Iterator[str]) -> str:
        """
        Stream text chunks live to the terminal.
        Appends chunks immediately using flush=True without redrawing stdout.
        Uses an in-memory io.StringIO buffer for efficient string accumulation.
        Returns the accumulated full response string for memory storage.
        """
        sys.stdout.write("Nexa: ")
        sys.stdout.flush()

        buffer = io.StringIO()
        for chunk in chunk_generator:
            sys.stdout.write(chunk)
            sys.stdout.flush()
            buffer.write(chunk)

        sys.stdout.write("\n\n")
        sys.stdout.flush()
        return buffer.getvalue()

    def render_static(self, text: str) -> str:
        """Render a deterministic, non-streamed response."""
        print(f"Nexa: {text}\n")
        return text
