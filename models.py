from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SourceNote:
    note_id: int
    model_name: str
    deck_name: str
    fields: dict[str, str]
    tags: list[str]

    def compact_text(self) -> str:
        field_lines = [f"{name}: {value}" for name, value in self.fields.items() if value.strip()]
        tags = " ".join(self.tags)
        return "\n".join(
            [
                f"Note ID: {self.note_id}",
                f"Model: {self.model_name}",
                f"Deck: {self.deck_name}",
                f"Tags: {tags}",
                *field_lines,
            ]
        ).strip()
