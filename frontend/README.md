# 🎥 Face Detection Stream — Frontend

React + Vite frontend for the real-time face detection system. Captures webcam video, streams frames over WebSocket, and displays the processed MJPEG feed with an ROI dashboard.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│  App.jsx                                            │
│  ├── VideoStreamer.jsx  → webcam → WS → backend     │
│  ├── <img> MJPEG       → processed video feed       │
│  └── ROI Dashboard     → polls /api/v1/roi/latest   │
└─────────────────────────────────────────────────────┘
```

### Components

| Component | Responsibility |
|-----------|---------------|
| `VideoStreamer` | Webcam capture via `getUserMedia`, canvas → JPEG conversion, WebSocket streaming to backend |
| `App` | Layout — MJPEG live feed display, ROI stats dashboard, status indicators |

---

## 📁 Source Structure

```
src/
├── main.jsx              # React entry point
├── index.css             # Design system — CSS custom properties, reset
├── App.jsx               # Main layout: video feed + ROI dashboard
├── App.css               # Layout styles (grid, cards, stats)
├── VideoStreamer.jsx      # Webcam → WebSocket streamer component
└── VideoStreamer.css      # Camera input UI styles
```

---

## ⚙️ VideoStreamer — How It Works

1. **Capture**: `navigator.mediaDevices.getUserMedia()` → `<video>` element
2. **Convert**: `<canvas>.toBlob("image/jpeg")` at ~10 FPS via `setInterval`
3. **Stream**: Raw JPEG `Blob` sent over WebSocket (binary, NOT base64)
4. **Reconnect**: Exponential backoff with jitter on WebSocket disconnect
5. **Cleanup**: Camera tracks stopped, intervals cleared, socket closed on unmount

### Key Design Choices

| Choice | Why |
|--------|-----|
| **Raw JPEG blobs** | Backend expects binary bytes — no base64 encoding overhead |
| **`useRef` for state in callbacks** | Prevents stale closures in WebSocket/setInterval handlers |
| **`canplay` event for readiness** | Deterministic video readiness vs arbitrary `setTimeout` |
| **Exponential backoff** | Prevents reconnect storms if backend is down |

---

## 🚀 Development

### Local dev (with hot reload)
```bash
npm install
npm run dev
```

The Vite dev server runs on `:3000` and proxies `/api/*` requests (including WebSocket) to `http://localhost:8000`.

### Production (via Docker)
```bash
# From project root
docker compose up --build
```

The frontend is built with `vite build` and served by nginx, which also reverse-proxies API/WebSocket requests to the backend.

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| **React 19** | UI framework |
| **Vite 8** | Build tool + dev server |
| **nginx** | Production static server + reverse proxy |
| **Vanilla CSS** | Custom properties, no CSS framework dependency |
