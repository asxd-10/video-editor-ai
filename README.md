# AI Video Editor - Hackathon Project

Production-grade video upload and processing platform with AI capabilities.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Redis
- FFmpeg

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Frontend Setup
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
```

### Run Application

**Terminal 1 - Redis:**
```bash
redis-server
```

**Terminal 2 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 3 - Celery Worker:**
```bash
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info
```

**Terminal 4 - Frontend:**
```bash
cd frontend
npm run dev
```

## 📱 Access
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🏗️ Tech Stack
- **Backend:** FastAPI, Celery, SQLAlchemy, FFmpeg
- **Frontend:** React, Tailwind CSS, Framer Motion
- **Queue:** Redis
- **Storage:** Local filesystem

## 📦 Features
- Video upload (drag & drop)
- Chunked uploads for large files
- Background processing
- Custom video player
- Thumbnail generation
- Proxy video creation
- Processing status tracking

## 🎯 Next Steps (Hackathon)
- [ ] Whisper transcription
- [ ] AI clip selection
- [ ] Auto-caption generation
- [ ] Retention optimization
- [ ] Multi-platform export

## 👥 Team
Avalanche Team 1 - foundry Start-Up In a Weekend Hackathon

Built at: 728 S Broad St, Philadelphia