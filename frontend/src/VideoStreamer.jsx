import { useState, useEffect, useRef, useCallback } from "react";

/**
 * VideoStreamer — Captures webcam frames and streams them as raw JPEG
 * binary over WebSocket to the backend face-detection pipeline.
 *
 * Props:
 *   wsUrl       — WebSocket endpoint (default: derived from current host)
 *   fps         — Target frame rate (default: 10)
 *   quality     — JPEG quality 0-1 (default: 0.7)
 *   width       — Canvas capture width (default: 640)
 *   height      — Canvas capture height (default: 480)
 *   onStatusChange — Optional callback(status: string)
 */

/** Connection states */
const Status = {
  IDLE: "idle",
  CONNECTING: "connecting",
  STREAMING: "streaming",
  RECONNECTING: "reconnecting",
  ERROR: "error",
};

/** Build the default WS URL from the current page location */
function getDefaultWsUrl() {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/api/v1/stream`;
}

/** Exponential backoff with jitter, capped at 30 s */
function backoff(attempt) {
  const base = Math.min(1000 * 2 ** attempt, 30_000);
  return base + Math.random() * 500;
}

export default function VideoStreamer({
  wsUrl,
  fps = 10,
  quality = 0.7,
  width = 640,
  height = 480,
  onStatusChange,
}) {
  const [status, setStatus] = useState(Status.IDLE);
  const [errorMsg, setErrorMsg] = useState(null);
  const [active, setActive] = useState(false);

  // Refs for mutable resources that survive re-renders
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const reconnectTimer = useRef(null);
  const reconnectAttempt = useRef(0);
  const unmounted = useRef(false);

  // ── Refs that mirror state to avoid stale closures ──
  const activeRef = useRef(false);
  const connectWsRef = useRef(null);

  useEffect(() => {
    activeRef.current = active;
  }, [active]);

  // Notify parent of status changes
  const updateStatus = useCallback(
    (next, err = null) => {
      setStatus(next);
      setErrorMsg(err);
      onStatusChange?.(next);
    },
    [onStatusChange]
  );

  // ── Cleanup helper ──
  const cleanup = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null; // prevent reconnect loop
      wsRef.current.close();
      wsRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    reconnectAttempt.current = 0;
  }, []);

  // ── Capture & send a single frame ──
  const captureFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (
      !video ||
      !canvas ||
      !wsRef.current ||
      wsRef.current.readyState !== WebSocket.OPEN ||
      video.readyState < 2 // HAVE_CURRENT_DATA
    ) {
      return;
    }

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert to JPEG blob, then send as binary
    canvas.toBlob(
      (blob) => {
        if (blob && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(blob);
        }
      },
      "image/jpeg",
      quality
    );
  }, [quality]);

  // ── Connect WebSocket ──
  const connectWs = useCallback(() => {
    if (unmounted.current) return;

    const url = wsUrl || getDefaultWsUrl();
    updateStatus(
      reconnectAttempt.current > 0 ? Status.RECONNECTING : Status.CONNECTING
    );

    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => {
      if (unmounted.current) return;
      reconnectAttempt.current = 0;
      updateStatus(Status.STREAMING);

      // Start frame capture loop
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = setInterval(captureFrame, 1000 / fps);
    };

    ws.onclose = () => {
      if (unmounted.current) return;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      // Use ref to check latest active state (avoids stale closure)
      if (activeRef.current) {
        const delay = backoff(reconnectAttempt.current);
        reconnectAttempt.current += 1;
        updateStatus(Status.RECONNECTING);
        reconnectTimer.current = setTimeout(() => {
          connectWsRef.current?.();
        }, delay);
      }
    };

    ws.onerror = () => {
      // onclose fires right after — reconnect handled there
    };
  }, [wsUrl, fps, captureFrame, updateStatus]);

  // Keep connectWsRef in sync so reconnect always calls latest version
  useEffect(() => {
    connectWsRef.current = connectWs;
  }, [connectWs]);

  // ── Start camera + WS ──
  const start = useCallback(async () => {
    cleanup();
    setActive(true);
    activeRef.current = true;
    setErrorMsg(null);
    updateStatus(Status.CONNECTING);

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: width }, height: { ideal: height } },
        audio: false,
      });

      if (unmounted.current) {
        mediaStream.getTracks().forEach((t) => t.stop());
        return;
      }

      streamRef.current = mediaStream;
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      const msg =
        err.name === "NotAllowedError"
          ? "Camera access denied. Please allow camera permissions."
          : err.name === "NotFoundError"
          ? "No camera found on this device."
          : `Camera error: ${err.message}`;
      updateStatus(Status.ERROR, msg);
      setActive(false);
      activeRef.current = false;
      return;
    }

    // Wait for video to be ready, then connect WebSocket
    const video = videoRef.current;
    if (video && video.readyState >= 3) {
      connectWsRef.current?.();
    } else if (video) {
      const onReady = () => {
        video.removeEventListener("canplay", onReady);
        if (!unmounted.current) connectWsRef.current?.();
      };
      video.addEventListener("canplay", onReady);
    } else {
      setTimeout(() => connectWsRef.current?.(), 300);
    }
  }, [cleanup, updateStatus, width, height]);

  // ── Stop ──
  const stop = useCallback(() => {
    setActive(false);
    activeRef.current = false;
    cleanup();
    updateStatus(Status.IDLE);
  }, [cleanup, updateStatus]);

  // ── Teardown on unmount ──
  useEffect(() => {
    unmounted.current = false;
    return () => {
      unmounted.current = true;
      activeRef.current = false;
      cleanup();
    };
  }, [cleanup]);

  // ── Render ──
  const isLive = status === Status.STREAMING;
  const isWorking =
    status === Status.CONNECTING || status === Status.RECONNECTING;

  return (
    <div className="streamer">
      <div className="streamer-header">
        <div className="streamer-title">
          <span>🎥</span> Camera Input
        </div>
        <div className="streamer-controls">
          <span className={`streamer-status ${status}`}>
            <span className="streamer-status-dot" />
            {status === Status.IDLE && "Off"}
            {status === Status.CONNECTING && "Connecting…"}
            {status === Status.STREAMING && "Streaming"}
            {status === Status.RECONNECTING && "Reconnecting…"}
            {status === Status.ERROR && "Error"}
          </span>
          <button
            id="camera-toggle"
            className={`streamer-btn ${active ? "stop" : "start"}`}
            onClick={active ? stop : start}
            disabled={isWorking}
          >
            {active ? "⏹ Stop Camera" : "▶ Start Camera"}
          </button>
        </div>
      </div>

      <div className="streamer-viewport">
        {/* Live preview */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`streamer-video ${isLive ? "visible" : ""}`}
        />

        {/* Hidden canvas for JPEG conversion */}
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          style={{ display: "none" }}
        />

        {/* Overlay states */}
        {status === Status.IDLE && !errorMsg && (
          <div className="streamer-overlay">
            <span className="streamer-overlay-icon">📷</span>
            <span>Press &quot;Start Camera&quot; to begin streaming</span>
          </div>
        )}
        {isWorking && (
          <div className="streamer-overlay">
            <span className="streamer-spinner" />
            <span>
              {status === Status.RECONNECTING
                ? "Reconnecting to server…"
                : "Starting camera…"}
            </span>
          </div>
        )}
        {status === Status.ERROR && errorMsg && (
          <div className="streamer-overlay error">
            <span className="streamer-overlay-icon">⚠️</span>
            <span>{errorMsg}</span>
          </div>
        )}
      </div>
    </div>
  );
}
