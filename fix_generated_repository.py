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

dto_path = Path("src/application/dtos/ticket_ingestion.py")
dto_content = dto_path.read_text(encoding="utf-8")
dto_content = dto_content.replace(
    "from datetime import datetime\n",
    "from datetime import datetime\nfrom enum import Enum\n",
)
dto_content = dto_content.replace(
    "return str(value).upper() if value is not None else value",
    "return value.value if isinstance(value, Enum) else (str(value).upper() if value is not None else value)",
)
dto_path.write_text(dto_content, encoding="utf-8")

test_path = Path("tests/application/use_cases/test_ticket_ingestion_use_case.py")
test_content = test_path.read_text(encoding="utf-8")
test_content = test_content.replace(
    "from src.domain.entities import CustomerEntity, TagEntity",
    "from src.domain.entities import (\n    CustomerEntity,\n    TagEntity,\n    TicketPriority,\n    TicketStatus,\n)",
)
test_content = test_content.replace('status="open"', "status=TicketStatus.OPEN")
test_content = test_content.replace('priority="high"', "priority=TicketPriority.HIGH")
test_path.write_text(test_content, encoding="utf-8")

Path(__file__).unlink()
