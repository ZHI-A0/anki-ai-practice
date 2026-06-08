# AI Practice for Anki

AI Practice is an Anki desktop add-on that generates AI-powered practice questions from selected Anki notes.

The first MVP focuses on this workflow:

1. Open Anki's **Browse** window.
2. Select notes/cards you want to practice.
3. Right-click the selection and choose **AI Practice: Generate from Selection**.
4. Choose a question type.
5. Generate cloze or Q&A practice using an OpenAI-compatible API.

## Features

- Adds an **AI Practice** context-menu item in Anki's Browse window.
- Also adds a global **AI Practice** menu under Anki's main Tools menu.
- Reads selected notes from Anki's Browser.
- Supports OpenAI-compatible `/chat/completions` endpoints.
- Generates either:
  - cloze / fill-in-the-blank practice
  - short-answer Q&A practice
- Displays answers and explanations in an Anki dialog.

## Current status

This is an early MVP. It is intended for local development and testing.

Not included yet:

- saving generated practice as new Anki notes
- automatic selection from recently reviewed cards
- streaming responses
- advanced prompt templates
- provider-specific UI

## Installation for local development

Clone this repository into Anki's add-ons folder.

Typical location:

- Windows: `%APPDATA%/Anki2/addons21/anki_ai_practice`
- macOS: `~/Library/Application Support/Anki2/addons21/anki_ai_practice`
- Linux: `~/.local/share/Anki2/addons21/anki_ai_practice`

Then restart Anki.

The directory should contain `__init__.py` directly:

```text
addons21/anki_ai_practice/__init__.py
addons21/anki_ai_practice/config.json
```

## Usage

Recommended MVP workflow:

```text
Browse → select notes/cards → right-click → AI Practice: Generate from Selection
```

The main Anki window also has:

```text
Tools → AI Practice → Generate from Active Browser Selection
```

The main-window menu is kept for later global workflows, such as generating practice from recently reviewed cards.

## Configuration

In Anki, open:

```text
Tools → Add-ons → AI Practice → Config
```

Example OpenAI configuration:

```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": "YOUR_API_KEY",
  "model": "gpt-4o-mini",
  "language": "zh-CN",
  "default_question_type": "cloze",
  "max_notes": 30,
  "temperature": 0.7
}
```

For other providers, use an OpenAI-compatible endpoint and set `base_url` and `model` accordingly.

## Development notes

Main files:

- `__init__.py` registers the menu actions and Browser context menu item.
- `note_selector.py` reads selected Browser notes.
- `prompt_builder.py` builds the LLM prompt.
- `llm_client.py` calls an OpenAI-compatible API.
- `practice_dialog.py` renders the generated practice.

## Privacy note

Selected note content is sent to the configured LLM API provider when you click **Generate Practice**. Do not use this add-on with private or sensitive notes unless you trust your configured provider.

## License

MIT
