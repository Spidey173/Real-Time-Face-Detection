# 🎯 Real-Time Face Detection Video Streaming System

A containerized, real-time computer vision system that ingests webcam frames, detects faces, draws bounding boxes (ROI), stores detection data, and streams processed video to a web client.

Built with a focus on **clean architecture, real-time performance, and pragmatic design tradeoffs**.

---

## 🚀 Quick Start (≤ 5 minutes)

### Requirements

* Docker & Docker Compose
* Webcam-enabled browser

### Run

```bash
docker compose up --build
```

### Open

* Frontend → http://localhost:3000
* API Docs → http://localhost:8000/docs
* Health → http://localhost:8000/health

---

## 🧠 What This System Does

* Captures webcam frames in the browser
* Streams frames to backend via WebSocket
* Detects a face in each frame
* Computes ROI (bounding box)
* Draws rectangle **without OpenCV**
* Stores ROI data in PostgreSQL
* Streams processed video back to frontend
* Displays live ROI metrics

---

## 🧱 Architecture

```text
Browser (React)
    │
    │ WebSocket (JPEG frames)
    ▼
FastAPI Backend
    │
    ├── Face Detection (MediaPipe)
    ├── ROI Computation
    ├── Bounding Box Rendering (NumPy)
    ├── DB Persistence (PostgreSQL)
    │
    ▼
MJPEG Stream (/video)
    │
    ▼
Frontend Display (<img>)
```

---

## 🔄 Data Flow

1. `getUserMedia()` captures webcam video
2. Frames → JPEG blobs (~10 FPS)
3. Sent via WebSocket (`/api/v1/stream`)
4. Backend:

   * Decode → NumPy array
   * Detect face (MediaPipe)
   * Compute ROI (normalized)
   * Draw bounding box (NumPy)
   * Store ROI in DB
5. Latest frame streamed via MJPEG
6. Frontend renders video + ROI dashboard

---

## 🔌 API Design

### 1. Frame Ingestion (Real-time)

```
WS /api/v1/stream
```

* Receives binary JPEG frames
* Returns per-frame acknowledgment

**Why WebSocket?**

* Avoids HTTP overhead per frame
* Enables continuous low-latency streaming

---

### 2. Processed Video

```
GET /api/v1/video
```

* MJPEG stream (`multipart/x-mixed-replace`)
* Works directly in `<img>` tag

**Why MJPEG instead of WebRTC?**

* Simpler
* No signaling server required
* Works out-of-the-box in browsers

---

### 3. ROI Data

```
GET /api/v1/roi
GET /api/v1/roi/latest
```

Supports:

* Pagination (`limit`, `offset`)
* Time filtering (`start`, `end`)
* Confidence filtering

---

## 🗄️ Database Schema

**Table: `face_detections`**

| Field         | Description         |
| ------------- | ------------------- |
| id            | Primary key         |
| timestamp     | Frame timestamp     |
| x, y          | Normalized position |
| width, height | ROI size            |
| confidence    | Detection score     |
| created_at    | Insert timestamp    |

**Design choice:**
Coordinates are normalized (0–1) → resolution-independent.

---

## ⚙️ Tech Stack

### Backend

* FastAPI (async API)
* MediaPipe (face detection)
* NumPy (fast bounding box rendering)
* Pillow (image encoding)
* SQLAlchemy (async ORM)
* PostgreSQL

### Frontend

* React + Vite
* WebSockets (streaming)
* MJPEG (`<img>` rendering)

### Infra

* Docker Compose
* Nginx (static + proxy)

---

## 🧠 Key Design Decisions

### No OpenCV

* Requirement constraint
* Replaced with:

  * MediaPipe → detection
  * NumPy → drawing

---

### WebSocket + MJPEG Hybrid

* WebSocket → ingestion (low latency)
* MJPEG → output (simple + reliable)

---

### In-memory frame sharing

* Latest frame stored in memory
* Avoids queue complexity
* Sufficient for single-instance deployment

---

### Async DB access

* Prevents blocking frame processing loop
* Each insert uses short-lived session

---

## ⚠️ Error Handling

* WebSocket disconnects handled gracefully
* DB failures do not interrupt streaming
* Input validation via Pydantic
* Backpressure protection (frame dropping)

---

## 🔒 Security Notes

* CORS enabled (should be restricted in production)
* Input validation enforced
* Future improvements:

  * Rate limiting
  * Auth for endpoints
  * Frame size limits

---

## 🧪 Testing

Covers:

* API endpoints (`/health`, `/roi`, `/video`)
* WebSocket streaming behavior
* MJPEG response validation
* Input validation errors

**Testing strategy:**

* In-memory SQLite DB
* Mocked face detector
* No external dependencies

---

## 📦 Project Structure

```text
app/
  api/
  services/
  db/
  models/
  schemas/

frontend/
  src/

tests/
docker-compose.yml
```

---

## 🤖 AI Usage Disclosure

AI tools were used for:

* Architecture refinement
* Code review assistance
* Documentation improvements

All implementation, debugging, and design decisions were made independently.

---

## 🏁 Summary

This project demonstrates:

* Real-time streaming system design
* Clean backend architecture (layered + async)
* Efficient frame processing pipeline
* Practical engineering tradeoffs

The system is **fully runnable, testable, and production-oriented**.

---
