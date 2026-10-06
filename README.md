# Deutsch-Friend — Developer & User Documentation

> An AI-powered German learning web app. Practise **Schreiben** (writing), **Sprechen** (speaking), **Hören** (listening) and **Lesen** (reading), look up words in a smart dictionary, and keep your account and preferences saved between sessions.

**Live demo:** <https://deutsch-friend.vercel.app>
**Source:** <https://github.com/themehmi/Deutsch-Friend>

---

## Table of Contents

1. [Overview](#1-overview)
2. [Feature Overview](#2-feature-overview)
3. [Tech Stack](#3-tech-stack)
4. [Architecture](#4-architecture)
5. [Project Structure](#5-project-structure)
6. [Installation & Setup](#6-installation--setup)
7. [Configuration](#7-configuration)
8. [Authentication & Accounts](#8-authentication--accounts)
9. [Page Routes](#9-page-routes)
10. [API Reference](#10-api-reference)
11. [Data Model](#11-data-model)
12. [User Guide](#12-user-guide)
13. [Error Handling](#13-error-handling)
14. [Security Considerations](#14-security-considerations)
15. [Known Limitations](#15-known-limitations)
16. [Deployment](#16-deployment)
17. [Extending the App](#17-extending-the-app)
18. [Roadmap Ideas](#18-roadmap-ideas)

---

## 1. Overview

Deutsch-Friend is a Flask application that pairs a classic server-rendered web UI with large-language-model features served through the [Groq API](https://console.groq.com/). It targets learners preparing for German exams and everyday communication, and covers all four exam skills plus grammar and vocabulary support.

What makes it different from a static course site:

- **Everything is generated on demand.** Writing tasks, listening scripts and reading texts are created fresh by an LLM, so practice material never runs out.
- **CEFR-aware.** Listening and reading exercises can be adapted to a chosen CEFR level (A1 and up).
- **Instant, explained feedback.** Written and spoken German is corrected with explanations in English.
- **Accounts and persistence.** Users sign up, log in, and have their preferences stored in MongoDB.

---

## 2. Feature Overview

| Area | Feature | Highlights |
| --- | --- | --- |
| **Accounts** | Sign up / log in / log out | Username or email login, hashed passwords, first-login tutorial flag |
| **Preferences** | Per-user key/value settings | Saved to and loaded from MongoDB |
| **Schreiben** | Writing task generator | Exam-style task in German with English translation and 3–4 required points |
| **Schreiben** | Writing corrector | Error explanations in English, corrected text, estimated CEFR level, HTML output |
| **Sprechen** | Speech-to-text | Whisper large-v3, tuned for German/English code-switching, optional language hint |
| **Sprechen** | Role-play chat partner | Stateless chat endpoint driven by a client-supplied system prompt |
| **Sprechen** | Spoken-sentence checker | Checks grammar **and** whether the sentence fits the scenario; returns a short correction or nothing if correct |
| **Hören** | Listening script generator | Presets (train station, weather, news, daily life) or a custom scenario, adjustable CEFR level |
| **Lesen** | Reading exercise generator | Text types (email, blog, news, story) or custom topic, plus 3 German comprehension questions, adjustable CEFR level |
| **Wörterbuch** | AI dictionary | German⇄English, articles for nouns, verb forms resolved to the infinitive with Partizip II, Präteritum, Futur I and Futur II |
| **Grammar** | Grammar dashboard | Dedicated page (`/grammar`) |

---

## 3. Tech Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| Web framework | **Flask 3.0.3** | Routing, sessions, templating, JSON APIs |
| Config | **python-dotenv 1.0.1** | Loads secrets from `.env` (values override existing environment variables) |
| Database | **MongoDB** via **pymongo** (+ **dnspython** for `mongodb+srv://` URIs) | User accounts and preferences |
| Password security | **Werkzeug** (`generate_password_hash`, `check_password_hash`) | Salted password hashing |
| HTTP clients | **requests**, plus `urllib` in two endpoints | Calls to Groq |
| AI – text | Groq chat completions, model `qwen/qwen3.8-27b` | Generation, correction, chat, dictionary |
| AI – speech | Groq transcription, model `whisper-large-v3` | Speech-to-text |
| Frontend | Jinja2 templates (HTML/CSS/JS) | One page per skill |

---

## 4. Architecture

```
┌──────────────┐  pages / forms   ┌───────────────────┐   HTTPS + Bearer key   ┌─────────────┐
│   Browser    │ ◄──────────────► │   Flask (app.py)  │ ─────────────────────► │  Groq API   │
│  (templates  │  fetch() JSON    │  routes + prompts │ ◄───────────────────── │ LLM/Whisper │
│   + JS)      │ ───────────────► │                   │          JSON          └─────────────┘
└──────────────┘                  └─────────┬─────────┘
                                            │ pymongo
                                            ▼
                                  ┌───────────────────┐
                                  │  MongoDB          │
                                  │  db: deutsch_app  │
                                  │  coll: users      │
                                  └───────────────────┘
```

**Request lifecycle**

1. The browser requests a page route (`/`, `/schreiben`, …) and Flask renders a Jinja2 template.
2. Page JavaScript calls an `/api/...` route using `fetch` (JSON, or multipart for audio).
3. Flask builds a task-specific system prompt, attaches the Groq API key and forwards the request.
4. The model output is trimmed and returned to the browser as a small JSON object.
5. Account-related data (users, preferences) is read from and written to MongoDB; login state lives in a signed Flask session cookie.

The server holds **no conversation state**. Chat history is kept by the client and sent in full with every `/api/chat` request.

---

## 5. Project Structure

```
Deutsch-Friend/
├── app.py              # Entire backend: auth, page routes, AI API routes
├── requirements.txt    # Flask, python-dotenv, requests, pymongo, dnspython
├── templates/          # Jinja2 pages
│   ├── index.html                # Home / dashboard (supports first-login tutorial)
│   ├── login.html                # Login form
│   ├── signup.html               # Registration form
│   ├── grammar_dashboard.html    # Grammar
│   ├── schreiben_dashboard.html  # Writing
│   ├── sprechen_dashboard.html   # Speaking
│   ├── hoeren_dashboard.html     # Listening
│   └── lesen_dashboard.html      # Reading
└── README.md
```

> The template file names above are the ones `app.py` renders. Their internal HTML/JS was not reviewed for this document, so frontend behaviour is described only where the backend makes it clear.

---

## 6. Installation & Setup

### Prerequisites

- Python 3.9 or newer
- A [Groq API key](https://console.groq.com/keys)
- A MongoDB database (e.g. a free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster) and its connection string

### Steps

```bash
# 1. Clone
git clone https://github.com/themehmi/Deutsch-Friend.git
cd Deutsch-Friend

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file (see Configuration)

# 5. Run
python app.py
```

The development server starts at **http://127.0.0.1:5000** with debug mode on.

---

## 7. Configuration

Create a `.env` file in the project root:

```env
API_KEY=your_groq_api_key
MongoDB=mongodb+srv://<user>:<password>@<cluster>/?retryWrites=true&w=majority
SECRET_KEY=a-long-random-string
```

| Variable | Required | Description |
| --- | --- | --- |
| `API_KEY` | Yes | Groq API key used for text generation and transcription |
| `MongoDB` | Yes | MongoDB connection URI. **The variable name is case-sensitive and is literally `MongoDB`** |
| `SECRET_KEY` | Strongly recommended | Signs the Flask session cookie. If unset, a hard-coded default is used, which is unsafe outside local development |

Notes:

- `load_dotenv(override=True)` means `.env` values win over variables already set in your shell.
- Without `MongoDB`, the app still starts, but signup and login report "Database connection failed", and because the home page requires a login, the app is effectively unusable.
- On startup the app tries to create **unique indexes** on `username` and `email`. If that fails, it prints a warning and continues.

---

## 8. Authentication & Accounts

Authentication is session-based and stored in the `users` collection.

### Sign up (`GET/POST /signup`)

Form fields: `username`, `email`, `password`.

Validation, in order:

1. Database must be connected.
2. Email must match a basic `name@domain.tld` pattern.
3. Password must be **at least 8 characters**.
4. Username must not already exist.
5. Email must not already be registered.

Username and email are trimmed and lower-cased. The password is stored only as a Werkzeug hash. New users get `is_first_login: true`. On success the user is redirected to the login page with a confirmation message.

### Log in (`GET/POST /login`)

Form fields: `username` (accepts **either username or email**) and `password`.

On success:

- `session['username']` is set and the session is marked permanent (Flask's default permanent lifetime is 31 days).
- If `is_first_login` is true, `session['show_tutorial']` is set and the flag is flipped to `false` in the database. The home page reads and clears this value once, so the tutorial is shown **only on the very first login**.

On failure the user sees "Invalid username or password." (the same message for unknown user and wrong password).

### Log out (`GET /logout`)

Removes `username` from the session and redirects to `/`, which in turn redirects to the login page.

### Flash messages

All feedback (validation errors, success notices) is delivered through Flask's `flash()` and rendered by the templates.

---

## 9. Page Routes

| Route | Methods | Template | Auth required | Purpose |
| --- | --- | --- | --- | --- |
| `/` | GET | `index.html` | **Yes** (redirects to `/login`) | Home dashboard; shows the tutorial on first login |
| `/signup` | GET, POST | `signup.html` | No | Registration |
| `/login` | GET, POST | `login.html` | No | Login |
| `/logout` | GET | – | No | Ends the session |
| `/grammar` | GET | `grammar_dashboard.html` | No\* | Grammar practice |
| `/schreiben` | GET | `schreiben_dashboard.html` | No\* | Writing practice |
| `/sprechen` | GET | `sprechen_dashboard.html` | No\* | Speaking practice |
| `/hoeren` | GET | `hoeren_dashboard.html` | No\* | Listening practice |
| `/lesen` | GET | `lesen_dashboard.html` | No\* | Reading practice |

\* Only the home page enforces login in the backend. See [Known Limitations](#15-known-limitations).

---

## 10. API Reference

- Request bodies are JSON unless stated otherwise (`/api/transcribe` uses multipart form data; `/api/get_preferences` is a `GET`).
- Successful responses are JSON objects. Failures return `{"error": "..."}` with an HTTP `4xx/5xx` status.
- AI endpoints call Groq with the model `qwen/qwen3.8-27b`.

### Quick reference

| Endpoint | Method | Skill | Login needed | API key source | Temp | Max tokens | Returns |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/save_preference` | POST | Account | Yes | – | – | – | `success` |
| `/api/get_preferences` | GET | Account | Yes (else `{}`) | – | – | – | preferences object |
| `/api/check_text` | POST | Schreiben | No | request body or `.env` | 0.2 | 1024 | `feedback` (HTML) |
| `/api/generate_scenario` | POST | Schreiben | No | request body or `.env` | 0.5 | 512 | `scenario` (HTML) |
| `/api/transcribe` | POST | Sprechen | No | `.env` | – | – | `text` |
| `/api/chat` | POST | Sprechen | No | `.env` | 0.5 | 256 | `reply` |
| `/api/check_speech` | POST | Sprechen | No | `.env` | 0.1 | 256 | `correction` (HTML or `null`) |
| `/api/generate_listen` | POST | Hören | No | `.env` | 0.7 | 128 | `transcript` |
| `/api/generate_lesen` | POST | Lesen | No | `.env` | 0.7 | 512 | `text` |
| `/api/dictionary` | POST | All | No | `.env` | 0.3 | 256 | `translation` |

---

### 10.1 `POST /api/save_preference`

Stores one preference for the logged-in user under `preferences.<key>`.

**Request**
```json
{ "key": "theme", "value": "dark" }
```

**Response**
```json
{ "success": true }
```

**Errors:** `401 {"error": "Unauthorized"}` if not logged in; `400 {"error": "Invalid data"}` if `key` or `value` is missing/falsy or the database is unavailable.

> Because the check is `if key and value`, falsy values such as `false`, `0` or `""` are rejected. Store booleans as strings (`"true"`/`"false"`) or extend the check.

---

### 10.2 `GET /api/get_preferences`

Returns the logged-in user's saved preferences.

**Response**
```json
{ "theme": "dark", "level": "A2" }
```

Returns `{}` when not logged in, when the database is unavailable, or when no preferences exist.

---

### 10.3 `POST /api/check_text` — writing correction

Grades a student's German text against a writing prompt.

**Request**
```json
{
  "prompt": "Schreibe eine E-Mail an einen Freund und lade ihn zum Essen ein.",
  "text": "Lieber Tom, ich möchte dich einladen …",
  "api_key": "optional"
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `text` | Yes | The student's German text |
| `prompt` | No | Defaults to `"Korrigiere den Text."` |
| `api_key` | No | Falls back to the server's `API_KEY` |

**Behaviour:** the model acts as a friendly expert teacher. It lists grammar, spelling and style errors, **explains them in English**, supplies the corrected German text and estimates a **CEFR level**. Output is requested as clean HTML (`<h3>`, `<ul>`, `<b>`, no code fences) so the frontend can insert it directly into the page.

**Response**
```json
{ "feedback": "<h3>Corrections</h3><ul>…</ul>" }
```

---

### 10.4 `POST /api/generate_scenario` — writing task generator

**Request**
```json
{ "topic": "booking a hotel room", "api_key": "optional" }
```

**Behaviour:** the topic may be written in English or German. The model returns a short, realistic task with 3–4 bullet points the student must cover. Instructions are in German with English translations in parentheses, formatted as simple HTML (`<p>`, `<ul>`).

**Response**
```json
{ "scenario": "<p>Sie möchten … (You want to …)</p><ul><li>…</li></ul>" }
```

---

### 10.5 `POST /api/transcribe` — speech-to-text

**Request:** `multipart/form-data`

| Field | Required | Description |
| --- | --- | --- |
| `audio` | Yes | Recorded audio file |
| `language` | No | Language hint such as `de` or `en` |

**Behaviour:** the audio is sent to Groq's transcription endpoint using `whisper-large-v3`. A priming prompt tells the model the speaker is a student mixing German and English, which improves accuracy for code-switching. Always uses the **server-side** `API_KEY`.

**Response**
```json
{ "text": "Hallo, wie geht es dir?" }
```

**Errors:** `400 {"error": "No audio file provided"}` when `audio` is missing.

---

### 10.6 `POST /api/chat` — conversation partner

A stateless chat endpoint for role-play.

**Request**
```json
{
  "system": "You are a waiter in a German restaurant. Reply in short, simple German.",
  "messages": [
    { "role": "user", "content": "Guten Tag, ich möchte einen Tisch reservieren." }
  ]
}
```

**Behaviour:** the `system` string is prepended to `messages` and sent to the model. Replies are capped at 256 tokens, which suits spoken dialogue. The client must resend the full history on each call.

**Response**
```json
{ "reply": "Natürlich! Für wie viele Personen?" }
```

---

### 10.7 `POST /api/check_speech` — spoken sentence checker

Checks a sentence the student just **spoke** (typically the output of `/api/transcribe`) for two things: relevance to the scenario and grammatical correctness.

**Request**
```json
{
  "text": "Ich möchte ein Tisch für zwei Personen.",
  "system": "Role-play: reserving a table in a restaurant"
}
```

| Field | Required | Description |
| --- | --- | --- |
| `text` | Yes | The spoken sentence. If empty, the endpoint returns `{"correction": null}` |
| `system` | No | Scenario context used to judge whether the sentence is on topic |

**Behaviour:** the model replies with exactly `OK` when the sentence is on topic and correct; the endpoint then returns `null`. Otherwise it returns a short HTML snippet with a corrected sentence (**✏️ Korrektur**) and an English explanation (**💡 Erklärung**).

**Response (needs correction)**
```json
{ "correction": "<b>✏️ Korrektur:</b> <span style='color:#7ee787'>Ich möchte einen Tisch für zwei Personen.</span><br><b>💡 Erklärung:</b> …" }
```

**Response (correct)**
```json
{ "correction": null }
```

The low temperature (0.1) keeps grading strict and consistent.

---

### 10.8 `POST /api/generate_listen` — listening exercise text

Generates a ~3-sentence German script that the frontend can read aloud (for example with browser text-to-speech).

**Request**
```json
{ "topic": "bahnhof", "level": "A2", "custom_prompt": "used only when topic is 'custom'" }
```

| Field | Default | Description |
| --- | --- | --- |
| `topic` | – | `bahnhof`, `wetter`, `nachrichten`, `alltag` or `custom` |
| `custom_prompt` | – | Scenario text, used when `topic` is `custom` |
| `level` | `A1` | CEFR level appended to the prompt ("Strictly adapt your vocabulary and grammar to the {level} CEFR language level") |

| Topic | Generated content |
| --- | --- |
| `bahnhof` | Train-station announcement (delay or platform change) |
| `wetter` | Weather report for tomorrow |
| `nachrichten` | Short news bulletin |
| `alltag` | Casual voice message from a friend |
| `custom` | Script based on `custom_prompt` |

Unknown topics fall back to "Write 3 short German sentences." The model is told to output **raw German only**: no markdown, no quotes, no translations.

**Response**
```json
{ "transcript": "Achtung an Gleis 3: Der Zug nach München hat zehn Minuten Verspätung." }
```

---

### 10.9 `POST /api/generate_lesen` — reading exercise

Generates a ~80-word German text followed immediately by 3 comprehension questions in German.

**Request**
```json
{ "topic": "email", "level": "B1", "custom_prompt": "used only when topic is 'custom'" }
```

| Field | Default | Description |
| --- | --- | --- |
| `topic` | `email` | `email`, `blog`, `news`, `story` or `custom` (unknown topics fall back to `email`) |
| `custom_prompt` | – | Text subject, used when `topic` is `custom` |
| `level` | `A1` | CEFR level appended to the prompt |

**Response**
```json
{ "text": "Hallo Anna, …\n\n1. Wohin fährt …?\n2. …\n3. …" }
```

> The preset prompts themselves say "B1-level" and the `level` instruction is appended afterwards. If you want the chosen level to be authoritative, remove "B1-level" from the presets.

---

### 10.10 `POST /api/dictionary` — German ⇄ English dictionary

**Request**
```json
{ "word": "gegangen" }
```

**Behaviour**

- German input is translated to English; English input to German, with **der/die/das** for nouns.
- Verbs in **any form** (`gegangen`, `mache`, `write`) are translated, the current grammatical form is identified, and the **infinitive** is given.
- The infinitive's **Partizip II, Präteritum, Futur I and Futur II** are always included.
- Output is kept free of conversational filler.

**Response**
```json
{ "translation": "to go — Partizip II of 'gehen'. Infinitive: gehen …" }
```

**Errors:** `400 {"error": "Word is missing."}` for an empty word; `400` if no API key is configured.

---

## 11. Data Model

Database `deutsch_app`, collection `users`:

```json
{
  "_id": "ObjectId",
  "username": "narinder",
  "email": "narinder@example.com",
  "password": "<werkzeug hash>",
  "is_first_login": false,
  "preferences": {
    "theme": "dark",
    "level": "A2"
  }
}
```

| Field | Notes |
| --- | --- |
| `username` | Lower-cased, **unique index** |
| `email` | Lower-cased, **unique index** |
| `password` | Hash only; plain text is never stored |
| `is_first_login` | `true` on creation; set to `false` after the first successful login |
| `preferences` | Created lazily by `/api/save_preference`; free-form keys |

---

## 12. User Guide

**Getting started**

1. Open the app and choose **Sign up**. Use a unique username, a valid email and a password of 8+ characters.
2. Log in with your username *or* email. First-time users see the tutorial once.
3. Pick a skill from the home dashboard.

**Schreiben (writing)**
1. Describe a topic and generate a writing task.
2. Write your answer and submit it.
3. Review the explained corrections, the corrected text and your estimated CEFR level.

**Sprechen (speaking)**
1. Choose a role-play scenario.
2. Record your speech; it is transcribed (German and English are both handled).
3. Your sentence is checked for grammar and relevance, and the AI partner replies so the conversation can continue.

**Hören (listening)**
1. Choose a topic and CEFR level, or enter a custom scenario.
2. Listen to the generated script and test your comprehension.

**Lesen (reading)**
1. Choose a text type, topic and CEFR level.
2. Read the text and answer the three German questions.

**Dictionary**
Type any German or English word, or any verb form, and get the translation, article and full set of tense forms.

---

## 13. Error Handling

| Situation | Status | Response |
| --- | --- | --- |
| No API key (`check_text`, `generate_scenario`, `generate_listen`, `generate_lesen`, `check_speech`, `dictionary`) | 400 | `{"error": "API Key is missing."}` |
| No audio in `/api/transcribe` | 400 | `{"error": "No audio file provided"}` |
| Empty word in `/api/dictionary` | 400 | `{"error": "Word is missing."}` |
| Not logged in on `/api/save_preference` | 401 | `{"error": "Unauthorized"}` |
| Invalid preference data | 400 | `{"error": "Invalid data"}` |
| Groq HTTP error in `check_text` / `generate_scenario` | 500 | `{"error": "HTTP <code>: <upstream body>"}` |
| Any other upstream or runtime exception | 500 | `{"error": "<message>"}` |
| Signup/login problems | – | Flash message, redirect back to the form |

Flash messages used by the auth flow: *Database connection failed*, *Invalid email address format*, *Password must be at least 8 characters long*, *Username already exists*, *Email already registered*, *Successfully registered. Please log in.*, *Invalid username or password.*

---

## 14. Security Considerations

**Already in place**
- Passwords are salted and hashed with Werkzeug.
- Unique indexes prevent duplicate usernames and emails.
- Login errors do not reveal whether the username or the password was wrong.
- Preference endpoints require an authenticated session.

**Recommended before a public launch**
- **Set a strong `SECRET_KEY`.** The built-in fallback is public in the source code, so anyone could forge session cookies.
- **Protect the AI endpoints.** Only `/` and the preference APIs check the session. Page routes and every `/api/*` AI route can be called without logging in, so anyone could spend your Groq quota. Add a login check and rate limiting (for example Flask-Limiter).
- **Add CSRF protection** to the signup and login forms (for example Flask-WTF).
- **Treat client-supplied API keys carefully.** `check_text` and `generate_scenario` accept `api_key` in the request body; keys then travel from the browser. Serve over HTTPS only, or remove this option.
- **Sanitise model-generated HTML.** `check_text`, `generate_scenario` and `check_speech` return HTML that is injected into the page. Sanitise it (for example with DOMPurify) before inserting it.
- **Disable debug mode in production.** `debug=True` exposes the Werkzeug debugger; use a production server such as Gunicorn.
- **Never commit `.env`** and rotate any key that has been exposed.
- **Use secure cookie flags** in production (`SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE`).

---

## 15. Known Limitations

| # | Limitation | Impact |
| --- | --- | --- |
| 1 | Login is only enforced on `/`; other pages and AI APIs are open | Unauthenticated access, quota abuse |
| 2 | `/api/transcribe` does not verify that `API_KEY` exists | A missing key results in an upstream authorization error instead of a clear message |
| 3 | `/api/chat` also skips the missing-key check | Same as above |
| 4 | `/api/save_preference` rejects falsy values | `false`, `0` and empty strings cannot be stored |
| 5 | Hard-coded model name in seven places | Changing models requires many edits |
| 6 | Mixed HTTP clients (`urllib` and `requests`) | Duplicated code, inconsistent error text |
| 7 | Reading presets say "B1-level" while a separate `level` is appended | Conflicting instructions to the model |
| 8 | `max_tokens` of 128 for listening scripts | Long scripts can be truncated |
| 9 | Hard-coded default `SECRET_KEY` | Insecure if the env variable is forgotten |
| 10 | Logout uses `GET` | Can be triggered by a cross-site link |
| 11 | No progress history, scoring or exercise storage | Results are not tracked between sessions |
| 12 | The grammar page has no dedicated backend endpoint | Grammar content is handled entirely on the frontend |

---

## 16. Deployment

The public demo is hosted on Vercel at <https://deutsch-friend.vercel.app>.

General checklist for any host:

1. Set `API_KEY`, `MongoDB` and `SECRET_KEY` as **environment variables** in the hosting dashboard (do not upload `.env`).
2. Allow your host's outbound IPs in MongoDB Atlas network access (or use `0.0.0.0/0` with strong credentials).
3. Run the app with a production WSGI server, for example:
   ```bash
   pip install gunicorn
   gunicorn app:app
   ```
4. Serve over HTTPS and enable secure cookie settings.
5. Remember that `app.run(...)` at the bottom of `app.py` only executes when the file is run directly, so it is ignored by WSGI servers.

---

## 17. Extending the App

**Adding a new AI feature**

1. If it needs its own page, add a route and a template:
   ```python
   @app.route('/new-skill')
   def new_skill():
       return render_template('new_skill_dashboard.html')
   ```
2. Add an API route that builds a system prompt, calls Groq and returns small JSON:
   ```python
   @app.route('/api/new_feature', methods=['POST'])
   def new_feature():
       data = request.json
       reply = call_groq(
           [{"role": "system", "content": "…"},
            {"role": "user", "content": data.get('input', '')}],
           temperature=0.5, max_tokens=256)
       return jsonify({"result": reply})
   ```
3. Call it from the page with `fetch('/api/new_feature', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({...})})`.

**Recommended refactor: one shared Groq helper**

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

This removes the repeated request code, the hard-coded model name and the `urllib`/`requests` split in one change, and makes it easy to add timeouts and logging.

**A login guard for protected routes**

```python
from functools import wraps

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped
```

Apply it to page routes, and return `401` JSON from a variant for `/api/*` routes.

---

## 18. Roadmap Ideas

- Progress tracking: store exercise history, CEFR estimates and streaks per user
- Saved vocabulary lists and spaced-repetition flashcards from dictionary lookups
- Listening comprehension questions and answer checking
- Server-side text-to-speech for listening scripts
- Exam simulation mode (timed Schreiben/Lesen sets)
- Rate limiting, CSRF protection and automated tests
- Configurable model and per-user CEFR level stored in `preferences`

---

*Documentation based on the `main` branch of `themehmi/Deutsch-Friend` (`app.py` and `requirements.txt`).*
