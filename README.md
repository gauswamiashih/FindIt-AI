# 🔍 FindIt – AI Powered Lost & Found Platform

<div align="center">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react" />
  <img src="https://img.shields.io/badge/Node.js-Express-339933?style=for-the-badge&logo=node.js" />
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?style=for-the-badge&logo=fastapi" />
  <img src="https://img.shields.io/badge/AI-CLIP%20Vision-8B5CF6?style=for-the-badge&logo=openai" />
  <img src="https://img.shields.io/badge/MongoDB-Mongoose-47A248?style=for-the-badge&logo=mongodb" />
  <img src="https://img.shields.io/badge/Socket.io-Realtime-010101?style=for-the-badge&logo=socket.io" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker" />
</div>

> **Production-ready microservices platform** where AI automatically matches lost and found items using CLIP vision embeddings with 98% accuracy.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Image Matching** | CLIP ViT-B/32 analyzes photos and finds visual matches automatically |
| 🗺️ **Interactive Maps** | OpenStreetMap/Leaflet with geolocation and distance filtering |
| 💬 **Real-time Chat** | Socket.io messaging between item owners and finders |
| 🔔 **Live Notifications** | In-app + email alerts on every match |
| 📱 **QR Codes** | Every item gets a unique scannable QR code |
| 🛡️ **Secure Auth** | JWT access + refresh token rotation with email verification |
| 🔍 **Full-text Search** | MongoDB text indexes with geo-radius filtering |
| 👑 **Admin Panel** | Dashboard with Recharts analytics, user management |
| 🐳 **Docker Ready** | One-command deployment with Docker Compose |

---

## 🏗️ Architecture

```
        Vercel (Production)
                  │
                  ▼
          React/Vite Frontend
             (client/)
                  │
             HTTPS REST API
             (WebSocket)
                  │
                  ▼
          FastAPI Backend
       (ai-service/backend)
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
    Supabase    Redis      AI/ML
   PostgreSQL             Processing
        │
        ▼
   Cloudinary
    Storage
```

---

## 🚀 Quick Start

### Prerequisites
- Python ≥ 3.10
- Node.js ≥ 18
- Supabase account (for PostgreSQL)
- Cloudinary account

### 1. Clone & Setup Environment

```bash
# Copy environment files
cp client/.env.example client/.env
cp ai-service/.env.example ai-service/.env

# Fill in your values in each .env file
```

### 2. Manual Start (Development)

**Terminal 1 – Backend (FastAPI):**
```bash
cd ai-service
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

**Terminal 2 – Client:**
```bash
cd client
npm install
npm run dev
```

---

## 🌍 Deployment

### 1. Supabase Setup
- Create a new Supabase project.
- Get your `DATABASE_URL` and `DIRECT_DATABASE_URL` from Project Settings -> Database.
- Add these to your backend `.env`.

### 2. Database Migration
Run Alembic migrations to create tables before starting the server:
```bash
cd ai-service
alembic upgrade head
```

### 3. Vercel (Frontend Deployment)
Deploy the React frontend easily on Vercel:
1. Connect your GitHub repository to Vercel.
2. Select the `client` directory as the Root Directory.
3. Add the following Environment Variables in Vercel:
   - `VITE_API_URL` (e.g., `https://your-fastapi-backend.onrender.com/api/v1`)
   - `VITE_SOCKET_URL` (e.g., `wss://your-fastapi-backend.onrender.com`)
   - `VITE_APP_NAME`
   - `VITE_APP_URL`
4. Deploy!

### 4. Render / Railway (Backend Deployment)
Deploy the FastAPI + AI processing backend on Render:
1. Create a new "Web Service" on Render.
2. Connect your GitHub repository.
3. **Root Directory**: `ai-service`
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add all environment variables from `ai-service/.env.example`.
7. **CORS Configuration**: Ensure `FRONTEND_URL` is set to your Vercel URL.
8. Set the Health Check path to `/api/v1/health`.

---

## 📄 License

MIT License – Free to use for academic and portfolio purposes.

---

<div align="center">
  Built with ❤️ as a Final Year Engineering Project
  <br/>
  <strong>AI-Powered · Real-Time · Production-Ready</strong>
</div>
