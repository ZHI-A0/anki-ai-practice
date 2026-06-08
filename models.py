from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SourceNote:
    note_id: int
    model_name: str
    deck_name: str
    fields: dict[str, str]
    tags: list[str]
    front_text: str = ""

    def first_field_text(self) -> str:
        for value in self.fields.values():
            if value.strip():
                return value
        return ""
