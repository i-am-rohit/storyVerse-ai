# StoryVerse AI

A production-ready Django platform for AI-powered story generation, audiobook creation, book summarization, and publishing.

## Features

| Module | URL | Description |
|--------|-----|-------------|
| Landing | `/` | Marketing homepage |
| Dashboard | `/dashboard/` | Stats, charts, activity timeline |
| Story Generator | `/stories/create/` | AI story creation with **live streaming** |
| Audiobook Studio | `/audiobooks/` | Voice selection & audio playback |
| Book Summarizer | `/books/summarizer/` | PDF/DOCX/TXT upload & summaries with **live progress** |
| Help | `/help/` | User guide |
| Accounts | `/accounts/` | Register, login, profile, social OAuth |
| Manage Users | `/accounts/users/` | Superuser-only user management |
| Admin | `/admin/` | Django admin panel |

### AI capabilities

- **Story generation** — Meta Llama 3.1/3.2 via local **Ollama** or cloud **Groq**; template fallback when LLM is off
- **Story continue** — Extend an existing story with streamed output
- **Book summarization** — Short summary, full book, chapter-wise, main points, short stories, reading guide
- **Real-time processing** — Progress bar + live token streaming during story and summary generation (SSE)
- **Audiobook narration** — ElevenLabs TTS (demo WAV fallback without API key)
- **Plain prose summaries** — No headings or metadata junk; optimized for read-aloud / audiobook conversion

---

## How to Run (Local Development)

### Prerequisites

- **Python 3.11+** (tested with 3.12)
- **pip** and **venv**
- **Ollama** (recommended for Llama story/summary features) — [https://ollama.com](https://ollama.com)
- No API keys required for demo/template mode

### Step 1 — Open the project

```bash
cd "story verse with audio generation"
```

### Step 2 — Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure environment

```bash
cp .env.example .env
```

### Step 5 — Start Ollama (recommended)

```bash
ollama serve          # if not already running
ollama pull llama3.2
```

Ensure `.env` contains:

```bash
LLM_ENABLED=true
LLM_PROVIDER=ollama
LLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

Set `LLM_ENABLED=false` to use template-based demo stories and local summary analysis without Ollama.

### Step 6 — Run database migrations

```bash
python manage.py migrate
```

### Step 7 — Create an admin user (optional)

```bash
python manage.py createsuperuser
```

### Step 8 — Start the development server

```bash
python manage.py runserver
```

Open in your browser:

- **Landing page:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Story Generator:** [http://127.0.0.1:8000/stories/create/](http://127.0.0.1:8000/stories/create/)
- **Book Summarizer:** [http://127.0.0.1:8000/books/summarizer/](http://127.0.0.1:8000/books/summarizer/)
- **Register:** [http://127.0.0.1:8000/accounts/register/](http://127.0.0.1:8000/accounts/register/)

### Quick test workflow

1. Register at `/accounts/register/` (or sign in with Google/Microsoft/Facebook if OAuth is configured)
2. **Story Generator** → enter a prompt → **Generate Story** → watch live progress and streamed text → **Save Story**
3. **Audiobook Studio** → select story → pick voice → **Generate Audio**
4. **Book Summarizer** → upload PDF/DOCX/TXT → choose **Full Book**, **Chapter Wise**, or **Generate All Summaries**
5. View stats on **Dashboard** → `/dashboard/`

---

## LLM Configuration (Llama)

Story writing and book summarization use **Meta Llama** through a unified client.

| Mode | `LLM_PROVIDER` | Requirements |
|------|----------------|--------------|
| **Local (recommended)** | `ollama` | Ollama running + model pulled (`ollama pull llama3.2`) |
| **Cloud (free tier)** | `groq` | `GROQ_API_KEY` from [console.groq.com](https://console.groq.com) |
| **Demo / offline** | — | `LLM_ENABLED=false` → template-based stories & local text analysis |

### Ollama setup

```bash
brew install ollama    # macOS
ollama serve
ollama pull llama3.2
```

### Groq setup

```bash
LLM_ENABLED=true
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your-groq-key
LLAMA_MODEL=llama-3.1-8b-instant
```

### Where Llama is used

| Feature | Service | Agent |
|---------|---------|-------|
| Story generate / continue | `apps/stories/services.py` | `agents/writer_agent.py` |
| Book summaries | `apps/books/services/summary_service.py` | `agents/summary_agent.py` |
| LLM HTTP client | — | `agents/llm_client.py` |
| System prompts | — | `agents/prompts.py` |

---

## Real-Time Streaming

Story and summary generation stream progress and text to the browser via **Server-Sent Events (SSE)**.

| Endpoint | Purpose |
|----------|---------|
| `POST /stories/generate/stream/` | Stream story generation |
| `POST /stories/continue/stream/` | Stream story continuation |
| `POST /books/generate/stream/` | Stream summary generation with step-by-step progress |

The UI shows:

- Progress bar and status messages (e.g. “Connecting to llama3.2…”, “Summarizing chapter 3/15…”)
- Live token streaming as Llama writes story or summary text

---

## API Keys & Optional Services

| Variable | Provider | Used for | Required? |
|----------|----------|----------|-----------|
| `LLM_ENABLED` | — | Enable Llama for stories/summaries | No (`false` = demo mode) |
| `LLM_PROVIDER` | Ollama / Groq | LLM backend | No (defaults to `ollama`) |
| `LLAMA_MODEL` | — | Model name | No (defaults to `llama3.2`) |
| `OLLAMA_BASE_URL` | Ollama | Local API URL | No |
| `GROQ_API_KEY` | Groq | Cloud Llama API | Only if `LLM_PROVIDER=groq` |
| `ELEVENLABS_API_KEY` | ElevenLabs | Audiobook TTS | No (demo WAV without key) |
| `ELEVENLABS_VOICE_ID` | ElevenLabs | Default narrator voice | No |
| `GOOGLE_OAUTH_*` | Google | Social login | No |
| `MICROSOFT_OAUTH_*` | Microsoft | Social login | No |
| `FACEBOOK_OAUTH_*` | Facebook | Social login | No |

Keys are read in `storyverse_ai/settings.py`.

---

## Project Structure

```
storyverse_ai/
├── manage.py
├── requirements.txt
├── .env.example
├── storyverse_ai/              # Django settings & URLs
│   └── settings.py
├── apps/
│   ├── dashboard/              # Analytics dashboard
│   ├── stories/                # Story generator + streaming views
│   ├── audiobooks/             # Audiobook studio
│   ├── books/                  # Book summarizer + streaming
│   ├── accounts/               # Auth, profiles, user management
│   └── common/                 # SSE helpers
├── agents/
│   ├── llm_client.py           # Ollama + Groq client (incl. streaming)
│   ├── writer_agent.py         # Story generation
│   ├── summary_agent.py        # Book summarization
│   ├── narration_agent.py      # ElevenLabs TTS
│   └── prompts.py              # System prompts (story creator, summarizer)
├── templates/
├── static/                     # CSS, JS (incl. sse-client.js)
└── media/                      # Uploads & generated audio
```

---

## Environment Variables Reference

```bash
# Django core
DJANGO_SECRET_KEY=change-me-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_LOG_LEVEL=INFO

# Llama (Ollama local — recommended)
LLM_ENABLED=true
LLM_PROVIDER=ollama
LLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434

# Llama (Groq cloud — alternative)
# LLM_PROVIDER=groq
# GROQ_API_KEY=gsk_your-groq-key
# LLAMA_MODEL=llama-3.1-8b-instant

# ElevenLabs TTS (optional)
ELEVENLABS_API_KEY=your-elevenlabs-key
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
ELEVENLABS_MODEL=eleven_multilingual_v2

# Social login (optional)
# GOOGLE_OAUTH_CLIENT_ID=
# GOOGLE_OAUTH_CLIENT_SECRET=
# MICROSOFT_OAUTH_CLIENT_ID=
# MICROSOFT_OAUTH_CLIENT_SECRET=
# FACEBOOK_OAUTH_CLIENT_ID=
# FACEBOOK_OAUTH_CLIENT_SECRET=

# Database (optional — SQLite is default)
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=storyverse_ai
# DB_USER=postgres
# DB_PASSWORD=
# DB_HOST=localhost
# DB_PORT=5432
```

---

## Authentication

| URL | Description |
|-----|-------------|
| `/accounts/register/` | Create a new account |
| `/accounts/login/` | Sign in (email/password or social OAuth) |
| `/accounts/logout/` | Sign out (GET or POST) |
| `/accounts/profile/` | View profile |
| `/accounts/users/login/` | Superuser login for Manage Users |
| `/oauth/` | django-allauth social OAuth routes |

All app pages (`/dashboard/`, `/stories/`, `/audiobooks/`, `/books/`) require login.

Sessions persist until explicit logout (`SESSION_COOKIE_AGE` defaults to 1 year).

---

## Book Summarizer

Upload **PDF**, **DOCX**, or **TXT** (max 10 MB). Available summary types:

| Type | Description |
|------|-------------|
| Short | 3–5 sentence overview |
| Full Book | Plain narrative summary, read-aloud ready |
| Chapter Wise | Short summary per chapter with % of book |
| Chapter Summary | Detailed per-chapter summaries |
| Main Points | Key takeaways by category |
| Short Stories | Mini stories inspired by each chapter |
| Reading Guide | How to approach the book |
| All | Generate every type above |

Summaries filter out Gutenberg boilerplate, table-of-contents junk, and metadata headings.

---

## Production Deployment

1. Set environment variables:

   ```bash
   DJANGO_DEBUG=False
   DJANGO_SECRET_KEY=<generate-a-strong-random-key>
   DJANGO_ALLOWED_HOSTS=yourdomain.com
   LLM_ENABLED=true
   LLM_PROVIDER=ollama          # or groq with GROQ_API_KEY
   ELEVENLABS_API_KEY=<your-key>  # if using real TTS
   ```

2. Collect static files:

   ```bash
   python manage.py collectstatic --noinput
   ```

3. Run with Gunicorn:

   ```bash
   gunicorn storyverse_ai.wsgi:application --bind 0.0.0.0:8000
   ```

---

## Static & Media Files

- **Static files** — served from `static/` in development; collected to `staticfiles/` in production via WhiteNoise.
- **Media uploads** — stored in `media/` (stories, summaries, book uploads, audio).

---

## External CDN Dependencies (no keys)

These load from CDN in the browser and need internet access but no API keys:

- Bootstrap 5, Bootstrap Icons
- Chart.js (dashboard)
- GSAP + AOS (landing page)
- Google Fonts

---

## License

Proprietary — StoryVerse AI.
