# Deutsch-Friend — Documentation

Deutsch-Fruend is a Flask web application for practising German across the four exam skills (**Schreiben, Sprechen, Hören, Lesen**), plus grammar and a built-in dictionary. The Flask backend serves HTML pages and acts as a thin proxy to the [Groq API](https://console.groq.com/), which provides both the LLM (text generation, correction, chat) and Whisper (speech-to-text).

> **Scope note:** This document is based on `app.py` and `requirements.txt`. The HTML/JS files in `templates/` were not reviewed, so frontend behaviour is described only where it can be inferred from the backend.

---

## 1. Project Structure

```
Deutsch-Fruend/
├── app.py              # Flask app: page routes + API routes (all logic)
├── requirements.txt    # Flask, python-dotenv, requests
├── templates/          # Jinja2/HTML pages (index + one dashboard per skill)
└── README.md
```

## 2. Tech Stack

| Component | Purpose |
|---|---|
| **Flask 3.0.3** | Web server, routing, JSON responses |
| **python-dotenv 1.0.1** | Loads `API_KEY` from a `.env` file |
| **requests** | HTTP calls to Groq (most endpoints) |
| **urllib** | HTTP calls to Groq (`check_text`, `generate_scenario`) |
| **Groq API** | LLM chat completions + `whisper-large-v3` transcription |
| **Model** | `qwen/qwen3.8-27b` (as configured in code) |

## 3. Architecture

```
┌────────────┐   HTML pages    ┌──────────────┐   HTTPS + Bearer key   ┌─────────────┐
│  Browser   │ ◄────────────── │  Flask app   │ ─────────────────────► │  Groq API   │
│ (templates)│ ── fetch(JSON)─►│   app.py     │ ◄───────────────────── │ LLM/Whisper │
└────────────┘                 └──────────────┘        JSON            └─────────────┘
```

1. The browser loads a page from a **page route** (`/`, `/grammar`, …).
2. JavaScript on that page calls an **API route** (`/api/...`) with JSON or form data.
3. Flask builds a prompt, adds the API key, and forwards the request to Groq.
4. Flask extracts the model output and returns a small JSON object to the browser.

## 4. Setup & Running

```bash
git clone https://github.com/themehmi/Deutsch-Fruend.git
cd Deutsch-Fruend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
API_KEY=your_groq_api_key_here
```

Run:

```bash
python app.py
```

The app starts at **http://127.0.0.1:5000** (debug mode on).

## 5. Configuration

| Variable | Where | Description |
|---|---|---|
| `API_KEY` | `.env` | Groq API key used for all LLM and transcription calls |

`load_dotenv(override=True)` means values in `.env` override any existing environment variable of the same name.

## 6. Page Routes

Each route simply renders a template.

| Route | Template | Purpose |
|---|---|---|
| `/` | `index.html` | Home / landing page |
| `/grammar` | `grammar_dashboard.html` | Grammar practice |
| `/schreiben` | `schreiben_dashboard.html` | Writing practice |
| `/sprechen` | `sprechen_dashboard.html` | Speaking practice |
| `/hoeren` | `hoeren_dashboard.html` | Listening practice |
| `/lesen` | `lesen_dashboard.html` | Reading practice |

## 7. API Reference

All endpoints are `POST`, accept JSON (except `/api/transcribe`, which takes multipart form data), and return JSON. On failure they return `{"error": "..."}` with status `400` or `500`.

### 7.1 `POST /api/check_text` — Writing correction (Schreiben)

Grades a student's German text against a writing prompt.

**Request**
```json
{
  "api_key": "optional – falls back to server API_KEY",
  "prompt": "Schreibe eine E-Mail an einen Freund…",
  "text": "Liebe Anna, ich möchte dich einladen…"
}
```

**Behaviour**
- Uses the system prompt: *friendly expert German teacher* → point out grammar/spelling/style errors, explain them **in English**, give the corrected German text, and estimate a **CEFR level** (A1, A2, B1…).
- Output is requested as **clean HTML** (`<h3>`, `<ul>`, `<b>`) with no code fences, so the frontend can inject it directly into a `<div>`.
- `temperature: 0.2`, `max_tokens: 1024` (low temperature for consistent grading).
- Default prompt if none is given: `"Korrigiere den Text."`

**Response**
```json
{ "feedback": "<h3>Corrections</h3><ul>…</ul>" }
```

### 7.2 `POST /api/generate_scenario` — Writing task generator

Creates an exam-style writing task from a topic.

**Request**
```json
{ "topic": "booking a hotel room", "api_key": "optional" }
```

**Behaviour**
- Produces a short realistic task plus **3–4 bullet points** the student must cover.
- Instructions are written in **German with English translations in parentheses**.
- Output is simple HTML (`<p>`, `<ul>`). `temperature: 0.5`, `max_tokens: 512`.

**Response**
```json
{ "scenario": "<p>…</p><ul>…</ul>" }
```

### 7.3 `POST /api/transcribe` — Speech-to-text (Sprechen)

Transcribes a recorded audio clip with Whisper.

**Request:** `multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `audio` | file | Recorded audio (required) |
| `language` | string | Optional language hint (e.g. `de`, `en`) |

**Behaviour**
- Sends the file to `https://api.groq.com/openai/v1/audio/transcriptions` using model `whisper-large-v3`.
- A priming `prompt` tells Whisper the speaker is a student mixing German and English, which improves accuracy for code-switching.
- Uses the **server-side** `API_KEY` only.

**Response**
```json
{ "text": "Hallo, wie geht es dir?" }
```

### 7.4 `POST /api/chat` — Conversation partner

A general chat endpoint used for conversational practice.

**Request**
```json
{
  "system": "You are a German waiter. Reply in simple German.",
  "messages": [
    { "role": "user", "content": "Guten Tag, ich möchte einen Tisch." }
  ]
}
```

**Behaviour**
- Prepends the caller-supplied `system` prompt to the message history and forwards it to the LLM.
- The conversation history lives on the **client**; the server is stateless.
- `temperature: 0.5`, `max_tokens: 256` (short replies suit spoken dialogue).

**Response**
```json
{ "reply": "Natürlich! Für wie viele Personen?" }
```

### 7.5 `POST /api/generate_listen` — Listening exercise text (Hören)

Generates a ~3-sentence German passage, which the frontend can then read aloud (e.g. text-to-speech) for the student to answer questions about.

**Request**
```json
{ "topic": "bahnhof", "custom_prompt": "only used when topic = custom" }
```

**Preset topics**

| `topic` | Generated content |
|---|---|
| `bahnhof` | Train-station announcement (delay / platform change) |
| `wetter` | Weather report for tomorrow |
| `nachrichten` | Short news bulletin |
| `alltag` | Casual voice message from a friend |
| `custom` | Uses `custom_prompt` as the scenario |

Unknown topics fall back to "Write 3 short German sentences." The system prompt forces **raw German text only** — no markdown, quotes, or translations. `temperature: 0.7`, `max_tokens: 128`.

**Response**
```json
{ "transcript": "Achtung am Gleis 3…" }
```

### 7.6 `POST /api/generate_lesen` — Reading exercise (Lesen)

Generates a **B1-level** German text (~80 words) followed by **3 comprehension questions in German**.

**Request**
```json
{ "topic": "email", "custom_prompt": "only used when topic = custom" }
```

**Preset topics:** `email`, `blog`, `news`, `story` (default is `email`), or `custom`.

`temperature: 0.7`, `max_tokens: 512`.

**Response**
```json
{ "text": "Hallo Tom, …\n\n1. Wohin fährt …?\n2. …" }
```

### 7.7 `POST /api/dictionary` — German ⇄ English dictionary

**Request**
```json
{ "word": "gegangen" }
```

**Behaviour**
- German input → English translation; English input → German (with **der/die/das** for nouns).
- For verbs in *any* form (e.g. `gegangen`, `mache`, `write`) it returns the translation, identifies the current grammatical form, gives the **infinitive**, and always includes **Partizip II, Präteritum, Futur I, and Futur II**.
- Output is meant to be concise, with no conversational filler. `temperature: 0.3`, `max_tokens: 256`.

**Response**
```json
{ "translation": "to go — Partizip II of 'gehen' …" }
```

### Endpoint summary

| Endpoint | Skill | Key source | Temp | Max tokens | Output |
|---|---|---|---|---|---|
| `/api/check_text` | Schreiben | request or `.env` | 0.2 | 1024 | HTML feedback |
| `/api/generate_scenario` | Schreiben | request or `.env` | 0.5 | 512 | HTML task |
| `/api/transcribe` | Sprechen | `.env` | – | – | Text |
| `/api/chat` | Sprechen | `.env` | 0.5 | 256 | Reply text |
| `/api/generate_listen` | Hören | `.env` | 0.7 | 128 | German text |
| `/api/generate_lesen` | Lesen | `.env` | 0.7 | 512 | Text + questions |
| `/api/dictionary` | All | `.env` | 0.3 | 256 | Translation text |

## 8. Typical User Flows

**Writing practice (Schreiben)**
1. Student enters a topic → `/api/generate_scenario` returns a task.
2. Student writes a response → `/api/check_text` returns corrections, the corrected text, and a CEFR estimate.

**Speaking practice (Sprechen)**
1. Browser records audio → `/api/transcribe` returns text.
2. Text is sent with a role-play system prompt to `/api/chat` → the AI replies, and the loop continues.

**Listening practice (Hören)**
1. Student picks a topic → `/api/generate_listen` returns a German transcript, which the page can play back as audio.

**Reading practice (Lesen)**
1. Student picks a text type → `/api/generate_lesen` returns a B1 text and three questions.

**Dictionary**
1. Student enters any word or verb form → `/api/dictionary` returns the translation and tense forms.

## 9. Error Handling

| Situation | Response |
|---|---|
| No API key available | `400` — `{"error": "API Key is missing."}` |
| No audio in `/api/transcribe` | `400` — `{"error": "No audio file provided"}` |
| Empty word in `/api/dictionary` | `400` — `{"error": "Word is missing."}` |
| Groq returns an HTTP error | `500` — error message (for `check_text` and `generate_scenario`, includes the upstream HTTP code and body) |
| Any other exception | `500` — `{"error": "<message>"}` |

## 10. Security & Maintenance Notes

- **Never commit `.env`.** Add it to `.gitignore` so your Groq key is not published.
- **Client-supplied keys:** `check_text` and `generate_scenario` accept an `api_key` in the request body. This is convenient for bring-your-own-key use, but keys then travel from the browser; use HTTPS if deployed.
- **No rate limiting or authentication.** If deployed publicly, anyone could consume your Groq quota through the endpoints that use the server key. Add auth and rate limits first.
- **Debug mode:** `app.run(debug=True)` is for development only. Use a production server (e.g. `gunicorn`) when deploying.
- **Injecting HTML:** `check_text` and `generate_scenario` return model-generated HTML that the frontend inserts into the page. Consider sanitising it (e.g. with DOMPurify) to guard against unsafe markup.
- **Model name:** The model ID `qwen/qwen3.8-27b` is hard-coded in seven places. Moving it to a single constant or environment variable makes future changes easier.
- **Mixed HTTP clients:** Two endpoints use `urllib` and the rest use `requests`. Standardising on `requests` would reduce duplicated code.

## 11. Extending the App

To add a new feature:

1. Add a page route and a template in `templates/` if it needs its own page.
2. Add an API route that builds a system prompt, calls Groq, and returns a small JSON object.
3. Call the new route from the page's JavaScript using `fetch`.

A shared helper such as `call_groq(messages, temperature, max_tokens)` would remove most of the repeated request code in `app.py`.
