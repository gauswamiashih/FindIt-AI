# 🔍 FindIt AI – Smart Lost & Found Platform

<div align="center">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react" />
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?style=for-the-badge&logo=fastapi" />
  <img src="https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=for-the-badge&logo=supabase" />
  <img src="https://img.shields.io/badge/AI-CLIP%20Vision-8B5CF6?style=for-the-badge&logo=openai" />
  <img src="https://img.shields.io/badge/Celery-Redis-37814A?style=for-the-badge&logo=celery" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker" />
</div>

---

## 📌 Overview

**FindIt AI** is an intelligent, full-stack Lost & Found platform that connects individuals who have lost personal belongings with those who have found them. Utilizing multimodal AI embeddings (OpenAI CLIP ViT-B/32), spatial geolocation algorithms, and real-time messaging, FindIt AI automatically analyzes item descriptions and images to calculate similarity scores and notify matching owners.

---

## ❓ Problem Statement

Traditional lost-and-found systems suffer from:
1. **Manual Keyword Matching Bottlenecks**: Searching for "blue bag" misses a report titled "navy backpack".
2. **Lack of Visual Search**: Standard databases store plain text without comparing physical product images.
3. **Privacy Risks**: Public notice boards expose owner phone numbers and personal contact details to scammers.
4. **Geographic Inaccuracy**: Items lost in specific campus buildings or urban parks are difficult to query by proximity.

FindIt AI addresses these challenges with automated multimodal AI vector matching, spatial Haversine radius filtering, privacy-preserving real-time chat, and QR code verification.

---

## ✨ Features

- 🤖 **Multimodal AI Matching**: PyTorch CLIP ViT-B/32 generates joint visual and textual embeddings for automated cosine similarity scoring.
- 🔐 **Supabase & Google Auth**: Secure JWT authentication supporting email/password and Google OAuth via Supabase Auth.
- 🗺️ **Geolocation & Map View**: Interactive Leaflet maps with Haversine Great Circle distance calculations for radius-based search.
- 💬 **Real-Time WebSocket Chat**: Dedicated encrypted-style chat rooms for match participants with message status tracking.
- 🔔 **Background Task Processing**: Celery & Redis queue offloads heavy AI inference from HTTP request threads.
- 📱 **QR Code Generator**: Instant PNG QR code generation for physical item tags leading to public lost item pages.
- 📊 **Admin Dashboard**: Analytics overview, user ban/unban moderation, role promotion, and item status management.
- 🛡️ **Production Hardening**: Rate limiting, image MIME validation, stack trace masking, and security isolation.

---

## 🏗️ Architecture

```
                       Vercel Deployment
                              │
                              ▼
                     React 19 Frontend
                         (client/)
                              │
                 REST API & Native WebSockets
                              │
                              ▼
                     FastAPI Backend API
                         (backend/)
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
  Supabase PostgreSQL    Redis Broker          Celery Worker
  (SQLAlchemy ORM)      (Task Queue)         (PyTorch / CLIP)
```

---

## 🛠️ Tech Stack

- **Frontend**: React 19, Vite, React Router v6, Tailwind CSS, Framer Motion, React Query, Leaflet Maps, Lucide Icons
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy ORM, Uvicorn, WebSockets
- **Database**: Supabase PostgreSQL (via SQLAlchemy)
- **AI & Vision**: PyTorch, Hugging Face Transformers (`openai/clip-vit-base-patch32`), Pillow, NumPy
- **Asynchronous Worker**: Celery, Redis
- **Testing & CI/CD**: Pytest, GitHub Actions CI
- **DevOps**: Docker, Docker Compose, Nginx

---

## 🧠 AI Matching Pipeline

1. **Multimodal Feature Extraction**: When an item is created, PyTorch CLIP processes the uploaded image and text description to compute normalized 512-dimensional vector embeddings.
2. **Cosine Similarity Computation**: High-dimensional vector dot-products generate visual similarity ($S_{image}$) and text similarity ($S_{text}$).
3. **Weighted Scoring Model**:
   $$S_{total} = (w_{image} \cdot S_{image}) + (w_{text} \cdot S_{text})$$
   *(Default weights: $w_{image} = 0.6$, $w_{text} = 0.4$)*
4. **Idempotency & Threshold Verification**: Matches exceeding a candidate similarity threshold ($S_{total} \ge 0.65$) trigger a notification task. Duplicate match pairs are prevented by unique constraints.

---

## 🔐 Authentication

Authentication is handled via Supabase Auth and verified in FastAPI:
- Frontend authenticates with Supabase (Email/Password or Google OAuth).
- Supabase issues JWT access tokens.
- FastAPI `get_current_user` dependency decodes and validates JWT signatures using `SUPABASE_SERVICE_ROLE_KEY` / `JWT_SECRET`.
- Validated users are automatically synced into PostgreSQL.

---

## 🗄️ Database

PostgreSQL database managed by SQLAlchemy models and Alembic migrations:
- **User**: User credentials, role (`user` / `admin`), status, and metadata.
- **Item**: Lost & Found items with title, description, category, status, coordinates (`latitude`, `longitude`), and Cloudinary image URLs.
- **Match**: AI-computed candidate matches with similarity score and confirmation status (`pending`, `confirmed`, `rejected`).
- **Notification**: Instant alerts pushed to item owners when a candidate match or chat message arrives.
- **Chat & Message**: Chat rooms linking confirmed match participants with real-time text exchange.

---

## 🔌 API Endpoints Summary

- `POST /api/v1/auth/register` – Register user
- `POST /api/v1/auth/login` – Login & receive JWT token
- `GET /api/v1/auth/me` – Retrieve current user
- `GET /api/v1/items` – List lost/found items with filters & pagination
- `POST /api/v1/items/form` – Create item with image upload
- `GET /api/v1/items/search` – Search items by query, category, and geo radius
- `POST /api/v1/matches/item/{id}/analyze` – Trigger AI matching
- `GET /api/v1/chats` – List user active chats
- `GET /api/v1/chats/ws/{chat_id}` – WebSocket chat connection
- `GET /api/v1/qr/item/{item_id}` – Generate QR code image
- `GET /api/v1/admin/stats` – Admin analytics metrics
- `GET /api/v1/health` – System health check

---

## 📁 Project Structure

```
FindIt-AI-Smart-Lost-Found-Platform/
├── client/                     # React 19 Frontend
│   ├── src/
│   │   ├── components/         # UI & Layout components
│   │   ├── context/            # Auth & WebSocket Contexts
│   │   ├── pages/              # Route pages (Dashboard, Admin, Chat, Item detail)
│   │   ├── services/           # Axios API client & services
│   │   └── utils/              # Helper utilities
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── backend/                    # Python FastAPI Backend
│   ├── app/
│   │   ├── api/                # API route controllers
│   │   ├── core/               # App config & security dependencies
│   │   ├── db/                 # Database engine & sessions
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic data schemas
│   │   ├── services/           # Business logic & CLIP embedding service
│   │   └── tasks/              # Celery background workers
│   ├── tests/                  # Pytest test suite (62 tests)
│   ├── requirements.txt
│   ├── alembic.ini
│   └── Dockerfile
│
├── .github/workflows/ci.yml    # GitHub Actions CI Workflow
├── docker-compose.yml          # Multi-container local orchestration
└── README.md
```

---

## ⚙️ Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Redis Server (optional for background tasks)

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
pytest tests/ -v
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd client
npm install
cp .env.example .env
npm run dev
```

---

## 🔑 Environment Variables

### Backend (`backend/.env`)
```ini
DATABASE_URL=postgresql://user:password@host:5432/postgres
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
JWT_SECRET=your-32-char-jwt-secret
FRONTEND_URL=http://localhost:3000
REDIS_URL=redis://localhost:6379/0
```

### Frontend (`client/.env`)
```ini
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_URL=http://localhost:8000/api/v1
```

---

## 🌐 Supabase & Google Login Setup

1. Create a project at [Supabase Dashboard](https://supabase.com).
2. Under **Authentication -> Providers**, enable **Google**.
3. Register OAuth 2.0 Credentials in Google Cloud Console with Redirect URI:
   `https://<your-supabase-project>.supabase.co/auth/v1/callback`
4. Copy `Client ID` and `Client Secret` into Supabase.

---

## 🐳 Docker Setup

Run the entire application stack locally using Docker Compose:

```bash
docker compose up --build
```

Services started:
- Frontend: `http://localhost:3000`
- FastAPI API: `http://localhost:8000`
- API Health Check: `http://localhost:8000/health`
- API Interactive Docs: `http://localhost:8000/docs`
- Redis Broker: `localhost:6379`

---

## ☁️ Deployment Guide

### Frontend Deployment (Vercel)
1. Import repository into Vercel.
2. Set Root Directory to `client`.
3. Framework Preset: `Vite`.
4. Configure Environment Variables:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_API_URL` (e.g. `https://findit-api.onrender.com/api/v1`)
5. Deploy.

### Backend Deployment (Render / Cloud Run)
1. Create Web Service pointing to `backend` folder.
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables from `backend/.env.example`.
5. Health Check Path: `/api/v1/health`.

---

## 🧪 Testing

The automated test suite in `backend/tests` validates authentication, item management, CLIP similarity vector scoring, search radius calculation, chat WebSockets, and security rate limiting:

```bash
cd backend
python -m pytest tests/ -v
```

*Results: 62 passed in < 7 seconds.*

---

## 🛡️ Security Audit

- **Authentication & JWT**: Verified on protected routes with signature validation.
- **Data Protection**: Stack trace suppression, parameter sanitization, rate limiting on sensitive POST endpoints.
- **Upload Safety**: Image uploads verified against permitted MIME types (`image/jpeg`, `image/png`, `image/webp`) with PIL content verification and 10MB size limits.

---

## ⚠️ Limitations

- High-resolution image CLIP feature extraction benefits from GPU acceleration; CPU inference execution timing scales linearly with task batch size.
- Real-time WebSocket connections require sticky session routing if deployed behind multi-instance load balancers without a Redis pub-sub backplane.

---

## 🔮 Future Improvements

- Integration of fine-tuned domain-specific vision transformers for localized merchandise detection.
- Automated OCR extraction for lost identity cards and license text.
- PWA push notification integration.

---

## 📄 License

MIT License – Free for academic, educational, and open-source use.
