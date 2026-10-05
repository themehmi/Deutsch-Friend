# Deutsch-Friend — Complete Project Documentation

> An AI-powered German practice platform built with Flask, MongoDB and the Groq API.
> Practise **Schreiben, Sprechen, Hören and Lesen**, drill grammar, and look up words with full verb conjugations — all at your own CEFR level.

**Repository:** <https://github.com/themehmi/Deutsch-Friend>
**Author:** [@themehmi](https://github.com/themehmi)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Feature Overview](#2-feature-overview)
3. [What's New](#3-whats-new)
4. [Tech Stack](#4-tech-stack)
5. [Architecture](#5-architecture)
6. [Repository Layout](#6-repository-layout)
7. [Installation & Setup](#7-installation--setup)
8. [Configuration Reference](#8-configuration-reference)
9. [Authentication & Sessions](#9-authentication--sessions)
10. [Database Schema](#10-database-schema)
11. [Page Routes](#11-page-routes)
12. [API Reference](#12-api-reference)
13. [AI Prompt Design](#13-ai-prompt-design)
14. [User Journeys](#14-user-journeys)
15. [Error Handling](#15-error-handling)
16. [Security Review & Hardening Checklist](#16-security-review--hardening-checklist)
17. [Deployment](#17-deployment)
18. [Troubleshooting](#18-troubleshooting)
19. [Extending the App](#19-extending-the-app)
20. [Roadmap Ideas](#20-roadmap-ideas)

---

## 1. Overview

Deutsch-Friend is a single-file Flask application (`app.py`) that acts as the backend for a set of HTML dashboards. The server has three jobs:

1. **Serve pages** — login, signup, a home screen, and one dashboard per skill.
2. **Manage users** — registration, login, sessions, a first-login tutorial flag, and saved preferences, all stored in MongoDB.
3. **Proxy AI requests** — build task-specific prompts and forward them to the Groq API (LLM chat completions and Whisper speech-to-text), returning small JSON responses to the browser.

The server keeps **no conversation state** — chat history lives in the browser and is sent with each request.

---

## 2. Feature Overview

| Area | What the learner can do | Backed by |
|---|---|---|
| **Accounts** | Sign up, log in with username *or* email, log out, see a one-time tutorial after the first login | MongoDB + Flask sessions |
| **Preferences** | Persist UI/learning settings per user and reload them later | `/api/save_preference`, `/api/get_preferences` |
| **Schreiben (Writing)** | Generate an exam-style writing task, write an answer, receive corrections, a corrected text and a CEFR estimate | `/api/generate_scenario`, `/api/check_text` |
| **Sprechen (Speaking)** | Record speech, get a transcription, role-play with an AI partner, and receive instant grammar/on-topic feedback on each spoken sentence | `/api/transcribe`, `/api/chat`, `/api/check_speech` |
| **Hören (Listening)** | Generate short German audio scripts (train station, weather, news, daily life, or custom) at a chosen CEFR level | `/api/generate_listen` |
| **Lesen (Reading)** | Generate reading texts (email, blog, news, story, or custom) with three comprehension questions, at a chosen CEFR level | `/api/generate_lesen` |
| **Grammar** | Dedicated grammar dashboard | `/grammar` page |
| **Dictionary** | German ⇄ English lookup with articles and automatic verb forms | `/api/dictionary` |

---

## 3. What's New

This documentation describes the **current** state of the code. Compared with the earlier, backend-only version of the app, the following are new:

- **User accounts** — `/signup`, `/login` and `/logout` with hashed passwords (Werkzeug), email-format validation, an 8-character minimum password, and unique username/email enforcement.
- **MongoDB persistence** — users are stored in the `deutsch_app` database (`users` collection) via `pymongo`; unique indexes are created on startup.
- **Login by username or email** — one input field accepts either.
- **Protected home page** — `/` redirects anonymous visitors to `/login`.
- **First-login tutorial** — new users get `is_first_login: true`; the first successful login sets a session flag so `index.html` can show a tutorial once.
- **Per-user preferences** — a key/value store under `preferences.*` on the user document.
- **CEFR level selection** — Hören and Lesen endpoints accept a `level` field (default `A1`) that is appended to the generation prompt.
- **Live speech checking** — new `/api/check_speech` endpoint validates a spoken sentence against the current role-play scenario, returning either nothing (correct) or a short HTML correction.
- **Updated dependencies** — `pymongo` and `dnspython` (needed for `mongodb+srv://` connection strings) were added.
- **Updated model** — all LLM calls use `qwen/qwen3.8-27b` through Groq.

---

## 4. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Web framework | **Flask 3.0.3** | Routing, sessions, Jinja2 templates |
| Config | **python-dotenv 1.0.1** | `load_dotenv(override=True)` — `.env` wins over OS variables |
| Database | **MongoDB** via **pymongo** | `dnspython` enables Atlas `mongodb+srv://` URIs |
| Password hashing | **Werkzeug** (`generate_password_hash`, `check_password_hash`) | Installed as a Flask dependency |
| HTTP clients | **requests** and **urllib** | `urllib` is used by `check_text` and `generate_scenario`; everything else uses `requests` |
| LLM | **Groq** chat completions, model `qwen/qwen3.8-27b` | Hard-coded in each endpoint |
| Speech-to-text | **Groq** `whisper-large-v3` | Audio transcription endpoint |
| Frontend | Jinja2 HTML templates + browser JavaScript | Located in `templates/` |

`requirements.txt`:

```text
Flask==3.0.3
python-dotenv==1.0.1
requests
pymongo
dnspython
```

---

## 5. Architecture

```text
┌───────────────┐   pages (HTML)    ┌─────────────────┐   Bearer key    ┌─────────────┐
│    Browser    │ ◄──────────────── │    Flask app    │ ──────────────► │  Groq API   │
│  (templates)  │ ── fetch (JSON) ► │     app.py      │ ◄────────────── │ LLM/Whisper │
└───────────────┘                   └────────┬────────┘      JSON       └─────────────┘
                                             │
                                             ▼
                                   ┌───────────────────┐
                                   │ MongoDB           │
                                   │ db: deutsch_app   │
                                   │ coll: users       │
                                   └───────────────────┘
```

**Request lifecycle for an AI feature**

1. The browser loads a dashboard route (for example `/lesen`).
2. Page JavaScript calls an `/api/...` endpoint with JSON (or `multipart/form-data` for audio).
3. Flask selects a system prompt, injects the CEFR level and parameters, and calls Groq with the server's `API_KEY`.
4. Flask trims the model output and returns a compact JSON object.
5. The page renders the result (some endpoints return HTML fragments meant to be injected directly).

**Graceful degradation:** if the `MongoDB` variable is not set, `users_collection` is `None`. Account pages still render, but signup/login show *"Database connection failed."* and the preference endpoints return empty/failed responses.

---

## 6. Repository Layout

```text
Deutsch-Friend/
├── app.py              # Entire backend: pages, auth, preferences, AI endpoints
├── requirements.txt    # Python dependencies
├── README.md           # Project readme
└── templates/          # Jinja2 pages
    ├── index.html              # Home (receives show_tutorial flag)
    ├── login.html              # Login form
    ├── signup.html             # Registration form
    ├── grammar_dashboard.html
    ├── schreiben_dashboard.html
    ├── sprechen_dashboard.html
    ├── hoeren_dashboard.html
    └── lesen_dashboard.html
```

> The template file names are taken from the `render_template(...)` calls in `app.py`. Their internal markup and JavaScript are not described here.

---

## 7. Installation & Setup

### Prerequisites

- Python 3.9+
- A [Groq](https://console.groq.com/) API key
- A MongoDB database (local, or a free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/themehmi/Deutsch-Friend.git
cd Deutsch-Friend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
API_KEY=your_groq_api_key
MongoDB=mongodb+srv://<user>:<password>@<cluster>/?retryWrites=true&w=majority
SECRET_KEY=replace_with_a_long_random_string
```

Generate a strong secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Run the app:

```bash
python app.py
```

Open <http://127.0.0.1:5000>. You will be redirected to `/login` — create an account at `/signup` first.

---

## 8. Configuration Reference

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `API_KEY` | **Yes** | – | Groq API key for chat completions and Whisper |
| `MongoDB` | **Yes** (for accounts) | – | MongoDB connection string. Note the exact, case-sensitive variable name |
| `SECRET_KEY` | Strongly recommended | `my_secret_key_123` | Signs Flask session cookies |

Other fixed settings in code:

| Setting | Value |
|---|---|
| Host / port | `127.0.0.1:5000` |
| Debug mode | `True` |
| Database name | `deutsch_app` |
| Collection | `users` |
| LLM model | `qwen/qwen3.8-27b` |
| Transcription model | `whisper-large-v3` |

---

## 9. Authentication & Sessions

### Signup — `POST /signup`

Form fields: `username`, `email`, `password`.

Validation order:

1. Database must be connected.
2. Email must match `^[^\s@]+@[^\s@]+\.[^\s@]+$`.
3. Password must be at least **8 characters**.
4. Username must not already exist.
5. Email must not already exist.

Usernames and emails are **trimmed and lower-cased** before storage. Passwords are stored only as Werkzeug hashes. On success the user is redirected to `/login` with a flash message.

### Login — `POST /login`

Form fields: `username` (accepts a username **or** an email) and `password`.

- On success: `session.permanent = True`, `session['username']` is set, and the user is sent to `/`.
- If `is_first_login` is `true`, the session gets `show_tutorial = True` and the database flag is flipped to `false`, so the tutorial appears exactly once.
- On failure: flash `Invalid username or password.` (the same message for unknown user and wrong password).

### Logout — `GET /logout`

Removes `username` from the session and redirects to `/` (which then redirects to `/login`).

### Home gating

`GET /` redirects to `/login` when no session exists. It pops `show_tutorial` from the session and passes it to `index.html`.

> **Note:** only `/` and the two preference endpoints check the session. The skill dashboards and AI endpoints are currently reachable without logging in — see [Security Review](#16-security-review--hardening-checklist).

---

## 10. Database Schema

**Database:** `deutsch_app` → **Collection:** `users`

```json
{
  "_id": "ObjectId",
  "username": "anna",
  "email": "anna@example.com",
  "password": "pbkdf2:sha256:...hash...",
  "is_first_login": false,
  "preferences": {
    "level": "B1",
    "theme": "dark"
  }
}
```

| Field | Type | Description |
|---|---|---|
| `username` | string, **unique** | Lower-cased handle |
| `email` | string, **unique** | Lower-cased email |
| `password` | string | Salted hash — never the plain password |
| `is_first_login` | bool | `true` until the first successful login |
| `preferences` | object | Arbitrary key/value pairs written by `/api/save_preference` (the example keys above are illustrative) |

Unique indexes on `username` and `email` are created at startup; failure to create them only prints a warning.

---

## 11. Page Routes

| Route | Methods | Template | Auth check | Description |
|---|---|---|---|---|
| `/` | GET | `index.html` | Redirects to login if no session | Home + optional tutorial |
| `/signup` | GET, POST | `signup.html` | – | Registration |
| `/login` | GET, POST | `login.html` | – | Sign in |
| `/logout` | GET | – | – | End session |
| `/grammar` | GET | `grammar_dashboard.html` | None | Grammar practice |
| `/schreiben` | GET | `schreiben_dashboard.html` | None | Writing practice |
| `/sprechen` | GET | `sprechen_dashboard.html` | None | Speaking practice |
| `/hoeren` | GET | `hoeren_dashboard.html` | None | Listening practice |
| `/lesen` | GET | `lesen_dashboard.html` | None | Reading practice |

---

## 12. API Reference

General conventions:

- Request bodies are JSON unless stated otherwise.
- Success responses are JSON objects; failures return `{"error": "..."}`.
- The server-side `API_KEY` is used for all Groq calls. Two endpoints (`check_text`, `generate_scenario`) will prefer an `api_key` supplied in the request body.

### 12.1 Preferences

#### `POST /api/save_preference` — requires login

```json
{ "key": "level", "value": "B1" }
```

Writes to `preferences.<key>` on the current user.

| Result | Response |
|---|---|
| Saved | `200` `{"success": true}` |
| Not logged in | `401` `{"error": "Unauthorized"}` |
| Missing `key`/`value` or no DB | `400` `{"error": "Invalid data"}` |

> Because the check is `if key and value`, falsy values such as `""`, `0` or `false` are rejected.

#### `GET /api/get_preferences`

Returns the saved preference object, or `{}` when the user is not logged in, the DB is unavailable, or nothing has been saved.

---

### 12.2 Schreiben (Writing)

#### `POST /api/generate_scenario`

Creates an exam-style writing task.

```json
{ "topic": "booking a hotel room", "api_key": "optional" }
```

- Task written in **German with English translations in parentheses**, plus 3–4 required bullet points.
- Output is HTML using `<p>` and `<ul>`.
- Parameters: `temperature 0.5`, `max_tokens 512`.

```json
{ "scenario": "<p>Sie möchten ein Hotelzimmer buchen… (You want to book…)</p><ul><li>…</li></ul>" }
```

#### `POST /api/check_text`

Grades a student's writing.

```json
{
  "prompt": "Schreibe eine E-Mail an einen Freund.",
  "text": "Liebe Anna, ich möchte dich einladen…",
  "api_key": "optional"
}
```

- `prompt` defaults to `"Korrigiere den Text."`.
- The model points out grammar/spelling/style errors **in English**, supplies the corrected German text and estimates a **CEFR level**.
- Output is clean HTML (`<h3>`, `<ul>`, `<b>`) with no code fences.
- Parameters: `temperature 0.2`, `max_tokens 1024`.

```json
{ "feedback": "<h3>Errors</h3><ul>…</ul><h3>Corrected text</h3>…<b>Estimated level: A2</b>" }
```

---

### 12.3 Sprechen (Speaking)

#### `POST /api/transcribe` — `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `audio` | file | Yes | Recorded clip |
| `language` | string | No | Language hint, e.g. `de` or `en` |

Sent to Groq's `audio/transcriptions` with `whisper-large-v3` and a priming prompt that tells Whisper the speaker is a learner mixing German and English.

```json
{ "text": "Hallo, ich möchte einen Kaffee bestellen." }
```

#### `POST /api/chat`

AI conversation partner.

```json
{
  "system": "You are a friendly waiter in a Berlin café. Reply in simple German.",
  "messages": [
    { "role": "user", "content": "Guten Tag! Ich hätte gern einen Kaffee." }
  ]
}
```

- The `system` prompt is prepended to the supplied history; the server stores nothing.
- Parameters: `temperature 0.5`, `max_tokens 256` — short, spoken-style replies.

```json
{ "reply": "Gern! Mit Milch oder ohne?" }
```

#### `POST /api/check_speech` *(new)*

Checks one spoken sentence for **relevance to the scenario** and **grammar**.

```json
{
  "text": "Ich habe gestern ins Kino gegangen.",
  "system": "Role-play: ordering food in a restaurant"
}
```

| Condition | Response |
|---|---|
| `text` empty | `200` `{"correction": null}` |
| Sentence correct *and* on topic (model replies exactly `OK`) | `200` `{"correction": null}` |
| Off topic or contains errors | `200` `{"correction": "<b>✏️ Korrektur:</b> <span style='color:#7ee787'>…</span><br><b>💡 Erklärung:</b> …"}` |
| No API key | `400` |

Parameters: `temperature 0.1`, `max_tokens 256` for consistent grading. The correction is an HTML snippet, ready to insert into the UI.

---

### 12.4 Hören (Listening)

#### `POST /api/generate_listen`

Generates a ~3-sentence German script (raw text, no markdown, no quotes, no translations) suitable for text-to-speech playback.

```json
{ "topic": "bahnhof", "level": "A2", "custom_prompt": "used only when topic = custom" }
```

| `topic` | Content |
|---|---|
| `bahnhof` | Train-station announcement (delay or platform change) |
| `wetter` | Weather report for tomorrow |
| `nachrichten` | Short news bulletin |
| `alltag` | Casual voice message from a friend |
| `custom` | Built from `custom_prompt` |

- `level` defaults to **`A1`**; the prompt appends *"Strictly adapt your vocabulary and grammar to the {level} CEFR language level."*
- Unknown topics fall back to *"Write 3 short German sentences."*
- Parameters: `temperature 0.7`, `max_tokens 128`.

```json
{ "transcript": "Achtung auf Gleis drei: Der Zug nach München hat zehn Minuten Verspätung." }
```

---

### 12.5 Lesen (Reading)

#### `POST /api/generate_lesen`

Generates a ~80-word text followed immediately by **three comprehension questions in German**.

```json
{ "topic": "blog", "level": "B1", "custom_prompt": "used only when topic = custom" }
```

| `topic` | Text type |
|---|---|
| `email` *(default)* | Email |
| `blog` | Blog post |
| `news` | Short news article |
| `story` | Short story |
| `custom` | Text about `custom_prompt` |

- `level` defaults to **`A1`** and is appended to the prompt.
- Parameters: `temperature 0.7`, `max_tokens 512`.

```json
{ "text": "Hallo Tom, …\n\n1. Wohin fährt …?\n2. …\n3. …" }
```

> **Prompt note:** the base prompts still say "B1-level" and the `level` instruction is appended afterwards. The two instructions can conflict (e.g. `level: "A1"` with a "B1-level" base prompt). Consider removing the hard-coded "B1" wording so the selected level is the only one.

---

### 12.6 Dictionary

#### `POST /api/dictionary`

```json
{ "word": "gegangen" }
```

- German input → English; English input → German (with **der/die/das** for nouns).
- For verbs in any form, returns the translation, the identified form, the **infinitive**, and always **Partizip II, Präteritum, Futur I and Futur II**.
- Parameters: `temperature 0.3`, `max_tokens 256`.

```json
{ "translation": "to go — Partizip II of 'gehen'. Perfekt: ist gegangen · Präteritum: ging · Futur I: wird gehen · Futur II: wird gegangen sein" }
```

*(The exact formatting comes from the model and may vary.)*

---

### Endpoint summary

| Endpoint | Method | Login required | Key used | Temp | Max tokens | Returns |
|---|---|---|---|---|---|---|
| `/api/save_preference` | POST | **Yes** | – | – | – | `success` |
| `/api/get_preferences` | GET | Soft (returns `{}`) | – | – | – | preferences |
| `/api/generate_scenario` | POST | No | body or `.env` | 0.5 | 512 | HTML |
| `/api/check_text` | POST | No | body or `.env` | 0.2 | 1024 | HTML |
| `/api/transcribe` | POST | No | `.env` | – | – | text |
| `/api/chat` | POST | No | `.env` | 0.5 | 256 | reply |
| `/api/check_speech` | POST | No | `.env` | 0.1 | 256 | HTML or `null` |
| `/api/generate_listen` | POST | No | `.env` | 0.7 | 128 | German text |
| `/api/generate_lesen` | POST | No | `.env` | 0.7 | 512 | text + questions |
| `/api/dictionary` | POST | No | `.env` | 0.3 | 256 | translation |

---

## 13. AI Prompt Design

| Endpoint | Persona / goal | Key constraints |
|---|---|---|
| `check_text` | Friendly expert German teacher | Explain in English, give corrected German, estimate CEFR, return clean HTML, **no** code fences |
| `generate_scenario` | German teacher creating exam tasks | German instructions with English in parentheses, 3–4 bullets, simple HTML |
| `chat` | Caller-defined | Prompt supplied by the page, so role-plays can change per scenario |
| `check_speech` | Strict but friendly grammar checker | Reply `OK` if correct and on-topic, otherwise a fixed two-line HTML format; no greetings or markdown |
| `generate_listen` | German text generator | Output **only** raw German; CEFR level appended |
| `generate_lesen` | German teacher | Text followed immediately by 3 questions; no markdown or English |
| `dictionary` | Bilingual dictionary | Translation + grammatical form + infinitive + four tense forms, no filler |

**Temperature strategy:** low values (0.1–0.3) for grading and lookup where consistency matters; moderate-to-higher values (0.5–0.7) for generation where variety is desirable.

---

## 14. User Journeys

**First visit**
`/signup` → `/login` → home with tutorial (shown once) → choose a skill.

**Writing**
Enter a topic → `generate_scenario` → write an answer → `check_text` → read corrections, corrected text and level.

**Speaking**
Pick a role-play (sets the `system` prompt) → record → `transcribe` → `check_speech` flags mistakes/off-topic answers → `chat` produces the partner's reply → repeat.

**Listening**
Choose topic + level → `generate_listen` → play the script with text-to-speech → answer questions on the page.

**Reading**
Choose text type + level → `generate_lesen` → read and answer the three questions.

**Dictionary**
Type any word or verb form → `dictionary` → translation and tense forms.

---

## 15. Error Handling

| Situation | Status | Body |
|---|---|---|
| Missing Groq key (endpoints that check) | `400` | `{"error": "API Key is missing."}` |
| Missing audio file | `400` | `{"error": "No audio file provided"}` |
| Empty dictionary word | `400` | `{"error": "Word is missing."}` |
| Invalid preference payload | `400` | `{"error": "Invalid data"}` |
| Preference save while logged out | `401` | `{"error": "Unauthorized"}` |
| Groq HTTP error (`check_text`, `generate_scenario`) | `500` | `HTTP <code>: <upstream body>` |
| Any other exception | `500` | `{"error": "<message>"}` |
| Auth form problems | redirect | Flash message on the same page |

**Known gaps:** `/api/transcribe` and `/api/chat` do not check for a missing key before calling Groq, so a missing key surfaces as a generic upstream `401` wrapped in a `500`. Several handlers also assume the JSON body exists; a request without JSON will raise an exception.

---

## 16. Security Review & Hardening Checklist

Priority items first.

| # | Issue | Why it matters | Fix |
|---|---|---|---|
| 1 | **Default `SECRET_KEY`** (`my_secret_key_123`) | Anyone who knows it can forge session cookies | Require `SECRET_KEY` and fail startup if missing |
| 2 | **AI endpoints are unauthenticated** | Anyone can spend your Groq quota | Add a `login_required` decorator and rate limiting (e.g. Flask-Limiter) |
| 3 | **Debug mode on** | Werkzeug debugger can expose code and enable remote execution | Use `debug=False` and a WSGI server in production |
| 4 | **No CSRF protection** on signup/login | Cross-site form submission | Add Flask-WTF / CSRF tokens |
| 5 | **Client-supplied `api_key`** in two endpoints | Keys travel through the browser | Remove, or serve strictly over HTTPS |
| 6 | **Model-generated HTML injected into the page** | Potential XSS if the model emits unsafe markup | Sanitise client-side (e.g. DOMPurify) |
| 7 | **No login throttling** | Password brute-forcing | Rate-limit `/login`, add lockout/back-off |
| 8 | **Session cookie flags** | Cookie theft over HTTP / XSS | Set `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE` |
| 9 | **Permanent sessions with default lifetime** | Long-lived logins | Set `PERMANENT_SESSION_LIFETIME` explicitly |
| 10 | **Arbitrary preference keys** | Users can write any `preferences.<key>` | Whitelist allowed keys and value types |
| 11 | **Hard-coded fallback `User-Agent: Mozilla/5.0`** | Harmless, but unnecessary noise | Optional cleanup |
| 12 | **Secrets in git** | Leaked Groq/Mongo credentials | Keep `.env` in `.gitignore`; rotate any key that was ever committed |

---

## 17. Deployment

### Production checklist

1. Set `debug=False` (or remove the `debug=True` argument).
2. Provide `API_KEY`, `MongoDB`, and a strong `SECRET_KEY` as real environment variables.
3. Serve with a production WSGI server:

   ```bash
   pip install gunicorn
   gunicorn -w 2 -b 0.0.0.0:8000 app:app
   ```

4. Put the app behind HTTPS (reverse proxy such as Nginx, Caddy or a platform router).
5. If using MongoDB Atlas, allow your server's IP in the Atlas network access list.
6. Add `.env` and `venv/` to `.gitignore`.

> `load_dotenv(override=True)` makes values in a local `.env` file **override** platform-level environment variables. On a host that injects its own variables, don't ship a `.env` file — or change this to `override=False`.

### Platform notes

- **Serverless hosts (e.g. Vercel):** the app is stateless apart from MongoDB and signed cookies, which suits serverless. Check function timeouts for slower LLM calls, and file-upload limits for audio.
- **Docker:** a minimal image only needs Python, `requirements.txt` and the `gunicorn` command above.

---

## 18. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "Database connection failed." on signup/login | `MongoDB` variable missing or wrong name | Use the exact name `MongoDB` in `.env` |
| `ServerSelectionTimeoutError` | IP not allowed in Atlas, or bad URI | Whitelist your IP; check credentials |
| `dnspython` / SRV errors | Missing `dnspython` | `pip install dnspython` |
| "API Key is missing." | `API_KEY` not set | Add it to `.env`, restart |
| `HTTP 401` from Groq | Invalid or revoked key | Generate a new key |
| `HTTP 400/404` mentioning the model | Model name unavailable on your Groq account | Change the model ID (it appears in several places) |
| Logged out unexpectedly after restart | `SECRET_KEY` changed or not set | Use a fixed `SECRET_KEY` |
| Reading text is at the wrong difficulty | "B1-level" wording conflicts with `level` | See the prompt note in [12.5](#125-lesen-reading) |
| Microphone upload fails | Browser blocked mic or unsupported format | Allow microphone access; test with a short `.webm`/`.wav` clip |
| Preference won't save | Value is falsy (`""`, `0`, `false`) | Send a non-empty string |

---

## 19. Extending the App

### Add a new skill or tool

1. Create `templates/<name>_dashboard.html`.
2. Add a page route in `app.py` (and protect it with a login check if desired).
3. Add an `/api/<name>` route that builds a prompt, calls Groq, and returns small JSON.
4. Call the endpoint from the page with `fetch`.

### Recommended refactor — one shared Groq helper

Most endpoints repeat the same request logic. A single helper removes the duplication, centralises the model name, and unifies `urllib`/`requests`:

```python
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

def call_groq(messages, temperature=0.5, max_tokens=256, api_key=None):
    key = api_key or os.getenv("API_KEY")
    if not key:
        raise ValueError("API Key is missing.")
    res = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages,
              "temperature": temperature, "max_tokens": max_tokens},
        timeout=30,
    )
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"].strip()
```

### Recommended refactor — login decorator

```python
from functools import wraps

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper
```

Apply `@login_required` to every `/api/*` route that consumes Groq quota.

---

## 20. Roadmap Ideas

- Progress tracking per skill (scores, streaks, CEFR trend) stored on the user document
- Persisting a user's chosen CEFR level and using it as the default for every generator
- Answer-checking for Lesen/Hören questions (currently the questions are generated but not graded server-side)
- Spaced-repetition word lists built from dictionary lookups
- Password reset by email and email verification
- Streaming responses for chat to reduce perceived latency
- Automated tests with mocked Groq responses
- Rate limiting and usage dashboards

---

*Documentation based on `app.py` and `requirements.txt` in the `main` branch of `themehmi/Deutsch-Friend`. The HTML/JavaScript templates were not accessible for review, so frontend behaviour is described only where it can be inferred from the backend.*
