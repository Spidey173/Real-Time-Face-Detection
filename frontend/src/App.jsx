import { useState, useEffect, useRef } from "react";
import "./App.css";
import "./VideoStreamer.css";
import VideoStreamer from "./VideoStreamer";

/**
 * API base — proxied to FastAPI via vite.config.js in dev.
 * In production, set VITE_API_URL to the real backend URL.
 */
const API = import.meta.env.VITE_API_URL || "";
const WS_URL = API ? API.replace(/^http/, "ws") + "/api/v1/stream" : undefined;

/** Video stream URL (MJPEG served directly by FastAPI) */
const STREAM_URL = `${API}/api/v1/video`;

/** ROI polling endpoint */
const ROI_URL = `${API}/api/v1/roi/latest`;

/** Polling interval in ms */
const POLL_INTERVAL = 1000;

function App() {
  const [roiData, setRoiData] = useState([]);
  const [streamOk, setStreamOk] = useState(false);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  // ── Fetch latest ROI data every second ──
  useEffect(() => {
    async function fetchROI() {
      try {
        const res = await fetch(`${ROI_URL}?count=5`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setRoiData(data);
        setError(null);
      } catch (err) {
        setError("Cannot reach backend");
      }
    }

    // Fetch immediately, then poll
    fetchROI();
    intervalRef.current = setInterval(fetchROI, POLL_INTERVAL);

    return () => clearInterval(intervalRef.current);
  }, []);

  // ── Latest detection (first item) ──
  const latest = roiData.length > 0 ? roiData[0] : null;

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <h1>Face Detection Stream</h1>
        <div className={`status-badge ${streamOk ? "" : "offline"}`}>
          <span className="status-dot" />
          {streamOk ? "Live" : "Waiting"}
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {/* Webcam capture → WebSocket streamer */}
      <VideoStreamer wsUrl={WS_URL} />

      {/* Main content */}
      <div className="main-grid">
        {/* Video panel */}
        <div className="video-panel">
          <div className="video-panel-header">
            <span>📹</span> Live Feed
          </div>
          <div className="video-container">
            <img
              src={STREAM_URL}
              alt="Live face detection stream"
              onLoad={() => setStreamOk(true)}
              onError={() => setStreamOk(false)}
            />
            {!streamOk && (
              <div className="video-placeholder">
                <span>📡</span>
                Waiting for camera stream...
              </div>
            )}
          </div>
        </div>

        {/* ROI Dashboard */}
        <aside className="roi-dashboard">
          {/* Latest detection card */}
          <div className="roi-card">
            <div className="roi-card-title">Latest Detection</div>
            {latest ? (
              <div className="stat-grid">
                <div className="stat-item">
                  <span className="stat-label">X</span>
                  <span className="stat-value">{latest.x.toFixed(3)}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Y</span>
                  <span className="stat-value">{latest.y.toFixed(3)}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Width</span>
                  <span className="stat-value accent">
                    {latest.width.toFixed(3)}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Height</span>
                  <span className="stat-value accent">
                    {latest.height.toFixed(3)}
                  </span>
                </div>
              </div>
            ) : (
              <div className="empty-state">No detections yet</div>
            )}
          </div>

          {/* Confidence card */}
          <div className="roi-card">
            <div className="roi-card-title">Confidence</div>
            {latest ? (
              <div className="stat-item">
                <span className="stat-value" style={{ fontSize: "1.6rem" }}>
                  {latest.confidence != null
                    ? `${(latest.confidence * 100).toFixed(1)}%`
                    : "—"}
                </span>
              </div>
            ) : (
              <div className="empty-state">—</div>
            )}
          </div>

          {/* Recent detections list */}
          <div className="roi-card">
            <div className="roi-card-title">Recent Detections</div>
            {roiData.length > 0 ? (
              <ul className="roi-list">
                {roiData.map((roi, i) => (
                  <li key={roi.id ?? i} className="roi-list-item">
                    <span className="roi-coords">
                      ({roi.x.toFixed(2)}, {roi.y.toFixed(2)}){" "}
                      {roi.width.toFixed(2)}×{roi.height.toFixed(2)}
                    </span>
                    <span className="roi-time">
                      {new Date(roi.timestamp).toLocaleTimeString()}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">Waiting for data...</div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

export default App;
