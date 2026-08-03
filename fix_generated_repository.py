from __future__ import annotations

from pathlib import Path


PATH = Path("src/infra/database/repositories.py")


def indent_range(content: str, start: str, end: str | None) -> str:
    start_index = content.find(start)
    if start_index < 0:
        raise RuntimeError(f"Could not find generated block start: {start!r}")
    if end is None:
        end_index = len(content)
    else:
        end_index = content.find(end, start_index)
        if end_index < 0:
            raise RuntimeError(f"Could not find generated block end: {end!r}")
    block = content[start_index:end_index]
    indented = "\n".join(
        f"    {line}" if line else line
        for line in block.split("\n")
    )
    return content[:start_index] + indented + content[end_index:]


content = PATH.read_text(encoding="utf-8")
content = indent_range(
    content,
    "\nasync def get_by_email(",
    "\n\nclass SqlAlchemyTicketRepository",
)
content = indent_range(
    content,
    "\nasync def get_by_external_ids(",
    "\n    async def set_ingestion_enabled(",
)
content = indent_range(
    content,
    "\nasync def synchronize_many(",
    "\n\nclass SqlAlchemyTagRepository",
)
content = indent_range(
    content,
    "\nasync def replace_many(",
    None,
)
PATH.write_text(content.rstrip() + "\n", encoding="utf-8")
Path(__file__).unlink()
