"use client";

import { useEffect, useState, useRef, useCallback } from "react";

interface TelemetryEvent {
  eventId: string;
  deviceId: string;
  temperature: number;
  humidity: number;
  vibration: number;
  pressure: number;
  machineState: string;
  timestamp: number;
  anomalyScore: number;
  severity: string;
  processingDecision: string;
  edgeCpu: number;
  networkLatency: number;
}

// ---------------------------------------------------------------------------
// Login Screen
// ---------------------------------------------------------------------------
function LoginForm({ onSuccess }: { onSuccess: (token: string) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("http://localhost:3000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.error ?? "Invalid credentials");
      }

      const { token } = await res.json();
      onSuccess(token);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      {/* Ambient glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Logo / Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 mb-4">
            <svg className="w-7 h-7 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-zinc-100 tracking-tight">EdgeSentinel</h1>
          <p className="text-zinc-500 text-sm mt-1">Sign in to access the dashboard</p>
        </div>

        {/* Card */}
        <div className="bg-zinc-900/80 backdrop-blur border border-zinc-800 rounded-2xl p-8 shadow-2xl shadow-black/50">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Error banner */}
            {error && (
              <div className="flex items-center gap-2.5 bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
                </svg>
                {error}
              </div>
            )}

            {/* Username */}
            <div>
              <label htmlFor="username" className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                className="w-full bg-zinc-800/60 border border-zinc-700 text-zinc-100 placeholder-zinc-600 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition"
              />
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-zinc-800/60 border border-zinc-700 text-zinc-100 placeholder-zinc-600 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition"
              />
            </div>

            {/* Submit */}
            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/40 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg text-sm transition-all duration-150 flex items-center justify-center gap-2 shadow-lg shadow-indigo-900/30"
            >
              {loading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  Authenticating…
                </>
              ) : (
                "Sign In"
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-zinc-600 text-xs mt-6">
          EdgeSentinel · Secure Industrial Monitoring
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Performance & Fault Lab Component
// ---------------------------------------------------------------------------
function FaultLab() {
  const [offline, setOffline] = useState(false);
  const [latencyMs, setLatencyMs] = useState(0);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  // Sync initial fault state from Edge Service
  useEffect(() => {
    fetch("http://localhost:8000/faults")
      .then((res) => res.json())
      .then((data) => {
        if (typeof data.offline === "boolean") setOffline(data.offline);
        if (typeof data.latency_ms === "number") setLatencyMs(data.latency_ms);
      })
      .catch((err) => console.warn("Could not connect to Edge Service at http://localhost:8000:", err));
  }, []);

  const sendFaultUpdate = useCallback(async (newOffline: boolean, newLatency: number) => {
    setUpdating(true);
    setStatusMsg(null);
    try {
      const res = await fetch("http://localhost:8000/faults", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          offline: newOffline,
          latency_ms: newLatency,
        }),
      });

      if (!res.ok) {
        throw new Error(`Edge responded with ${res.status}`);
      }

      setStatusMsg("Fault state updated on Edge Node");
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg(`Failed to contact Edge (port 8000): ${err.message}`);
    } finally {
      setUpdating(false);
    }
  }, []);

  const handleToggleOffline = () => {
    const nextVal = !offline;
    setOffline(nextVal);
    sendFaultUpdate(nextVal, latencyMs);
  };

  const handleLatencyChange = (val: number) => {
    setLatencyMs(val);
    sendFaultUpdate(offline, val);
  };

  return (
    <div className="bg-zinc-900/60 backdrop-blur border border-zinc-800 rounded-xl p-5 mb-8 shadow-xl">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-zinc-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.67 2.67 0 0021 17.25l-5.87-5.83m-1.71 1.75l-4.25-4.25m0 0L3 3m6.17 6.17l4.25 4.25" />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
              Performance &amp; Fault Lab
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                Resilience Testing
              </span>
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Inject cloud outages &amp; latency to test edge adaptive routing and offline sync.
            </p>
          </div>
        </div>

        {/* Real-time status badges */}
        <div className="flex items-center gap-2">
          {updating && (
            <span className="text-xs font-mono text-zinc-400 animate-pulse flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
              Syncing…
            </span>
          )}
          {statusMsg && !updating && (
            <span className="text-xs font-mono text-indigo-400">
              {statusMsg}
            </span>
          )}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-800/80 border border-zinc-700/60 text-xs">
            <span className="text-zinc-500 font-mono">Edge Target:</span>
            <span className="font-mono text-zinc-300">localhost:8000</span>
          </div>
        </div>
      </div>

      {/* Controls Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-5">
        {/* Control 1: Simulate Cloud Outage */}
        <div className={`p-4 rounded-lg border transition-all duration-200 ${
          offline
            ? "bg-red-950/20 border-red-500/40 shadow-lg shadow-red-950/20"
            : "bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700"
        }`}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-zinc-200">
                  Simulate Cloud Outage
                </span>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                    offline
                      ? "bg-red-500/20 text-red-400 border border-red-500/30"
                      : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  }`}
                >
                  {offline ? "OUTAGE ACTIVE" : "ONLINE"}
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                Forces edge node to raise connection errors, caching telemetry in SQLite outbox until connection is restored.
              </p>
            </div>

            {/* Toggle switch */}
            <button
              type="button"
              role="switch"
              aria-checked={offline}
              onClick={handleToggleOffline}
              className={`relative inline-flex h-6 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-red-500/50 ${
                offline ? "bg-red-600" : "bg-zinc-700"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                  offline ? "translate-x-6" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {offline && (
            <div className="mt-3 pt-3 border-t border-red-900/40 flex items-center gap-2 text-xs text-red-300">
              <svg className="w-4 h-4 shrink-0 text-red-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
              <span>Outage simulation active: Events are buffering in SQLite outbox. Turn off to trigger automatic sync.</span>
            </div>
          )}
        </div>

        {/* Control 2: Simulate Network Latency */}
        <div className={`p-4 rounded-lg border transition-all duration-200 ${
          latencyMs > 200
            ? "bg-amber-950/20 border-amber-500/40"
            : "bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700"
        }`}>
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-sm font-semibold text-zinc-200">
              Simulate Network Latency
            </span>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded">
                {latencyMs} ms
              </span>
              {latencyMs > 200 && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-bold">
                  EDGE ROUTING FORCED
                </span>
              )}
            </div>
          </div>

          <p className="text-xs text-zinc-400 mb-3 leading-relaxed">
            Delays HTTP forwarding. When &gt; 200ms, the edge decision engine adaptively switches routing to EDGE.
          </p>

          {/* Slider */}
          <div className="space-y-3">
            <input
              type="range"
              min="0"
              max="1000"
              step="25"
              value={latencyMs}
              onChange={(e) => handleLatencyChange(Number(e.target.value))}
              className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-indigo-500 focus:outline-none"
            />

            {/* Quick preset buttons */}
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-400">
              <span className="text-zinc-500 mr-1">Presets:</span>
              <button
                type="button"
                onClick={() => handleLatencyChange(0)}
                className={`px-2 py-0.5 rounded border transition ${
                  latencyMs === 0
                    ? "bg-indigo-600 text-white border-indigo-500"
                    : "bg-zinc-800 text-zinc-400 border-zinc-700 hover:text-zinc-200"
                }`}
              >
                0ms (Normal)
              </button>
              <button
                type="button"
                onClick={() => handleLatencyChange(100)}
                className={`px-2 py-0.5 rounded border transition ${
                  latencyMs === 100
                    ? "bg-indigo-600 text-white border-indigo-500"
                    : "bg-zinc-800 text-zinc-400 border-zinc-700 hover:text-zinc-200"
                }`}
              >
                100ms
              </button>
              <button
                type="button"
                onClick={() => handleLatencyChange(250)}
                className={`px-2 py-0.5 rounded border transition ${
                  latencyMs === 250
                    ? "bg-indigo-600 text-white border-indigo-500"
                    : "bg-zinc-800 text-zinc-400 border-zinc-700 hover:text-zinc-200"
                }`}
              >
                250ms (&gt;200)
              </button>
              <button
                type="button"
                onClick={() => handleLatencyChange(500)}
                className={`px-2 py-0.5 rounded border transition ${
                  latencyMs === 500
                    ? "bg-indigo-600 text-white border-indigo-500"
                    : "bg-zinc-800 text-zinc-400 border-zinc-700 hover:text-zinc-200"
                }`}
              >
                500ms (High)
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------
export default function Dashboard() {
  const [token, setToken] = useState<string | null>(null);
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sseRef = useRef<EventSource | null>(null);

  // Once authenticated, fetch history + open SSE
  useEffect(() => {
    if (!token) return;

    setLoading(true);

    // Fetch the 50 most recent events
    const fetchInitialTelemetry = async () => {
      try {
        const res = await fetch("http://localhost:3000/api/v1/telemetry", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to fetch");
        const data = await res.json();
        setEvents(data);
        setError(null);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchInitialTelemetry();

    // EventSource cannot send headers — pass token via query param
    const sse = new EventSource(
      `http://localhost:3000/api/v1/telemetry/stream?token=${token}`
    );
    sseRef.current = sse;

    sse.onmessage = (event) => {
      try {
        const newEvent = JSON.parse(event.data);
        setEvents((prev) => {
          const updated = [newEvent, ...prev];
          return updated.length > 50 ? updated.slice(0, 50) : updated;
        });
        setError(null);
      } catch (e) {
        console.error("Error parsing SSE data", e);
      }
    };

    sse.onerror = () => {
      setError("SSE stream disconnected. Reconnecting…");
    };

    return () => {
      sse.close();
      sseRef.current = null;
    };
  }, [token]);

  // Show login screen until we have a token
  if (!token) {
    return <LoginForm onSuccess={setToken} />;
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 font-sans p-4 md:p-8">
      <header className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-zinc-100">
            EdgeSentinel Dashboard
          </h1>
          <p className="text-zinc-400 mt-1 text-sm md:text-base">Real-time Telemetry &amp; Routing</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Live indicator */}
          <div className="flex items-center space-x-2 bg-zinc-900 px-4 py-2 rounded-lg border border-zinc-800">
            <div
              className={`w-2.5 h-2.5 rounded-full ${
                loading
                  ? "bg-amber-500 animate-pulse"
                  : error
                  ? "bg-red-500"
                  : "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)] animate-pulse"
              }`}
            />
            <span className="text-sm font-medium text-zinc-300">
              {loading ? "Connecting…" : error ? "Disconnected" : "Live Stream (SSE)"}
            </span>
          </div>

          {/* Sign out */}
          <button
            id="signout-btn"
            onClick={() => {
              sseRef.current?.close();
              setToken(null);
              setEvents([]);
            }}
            className="flex items-center gap-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 text-sm px-3 py-2 rounded-lg transition"
            title="Sign out"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
            </svg>
            Sign out
          </button>
        </div>
      </header>

      {/* Performance & Fault Lab */}
      <FaultLab />

      {/* Main Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left whitespace-nowrap">
            <thead className="text-xs uppercase bg-zinc-900/80 text-zinc-400 border-b border-zinc-800">
              <tr>
                <th className="px-6 py-4 font-semibold tracking-wider">Timestamp</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Device ID</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Latency (ms)</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Severity</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Anomaly Score</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Processing Decision</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-zinc-500">
                    Waiting for telemetry data…
                  </td>
                </tr>
              ) : (
                events.map((e, idx) => {
                  let rowClasses = "hover:bg-zinc-800/40 transition-colors";
                  let severityBadge = "";

                  if (e.severity === "CRITICAL") {
                    rowClasses += " bg-red-950/10";
                    severityBadge = "bg-red-500/20 text-red-500 border border-red-500/30 font-bold";
                  } else if (e.severity === "WARNING") {
                    severityBadge = "bg-amber-500/20 text-amber-500 border border-amber-500/30 font-semibold";
                  } else {
                    severityBadge = "bg-green-500/10 text-green-400 border border-green-500/20 font-medium";
                  }

                  const isHighLatency = e.networkLatency > 200;

                  return (
                    <tr key={e.eventId || idx} className={rowClasses}>
                      <td className="px-6 py-4 font-mono text-xs text-zinc-400">
                        {new Date(e.timestamp > 1e11 ? e.timestamp : e.timestamp * 1000).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 font-medium text-zinc-200">{e.deviceId}</td>
                      <td className="px-6 py-4 font-mono text-xs">
                        <span className={`px-2 py-0.5 rounded font-bold ${
                          isHighLatency
                            ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                            : "text-zinc-300"
                        }`}>
                          {e.networkLatency?.toFixed(1) ?? "--"} ms
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded text-xs tracking-wide ${severityBadge}`}>
                          {e.severity}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-blue-400">
                        {e.anomalyScore?.toFixed(4) ?? "--"}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`px-2 py-1 rounded text-xs font-bold tracking-wider ${
                            e.processingDecision === "EDGE"
                              ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                              : e.processingDecision === "CLOUD"
                              ? "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                              : "bg-zinc-700/50 text-zinc-300 border border-zinc-600/50"
                          }`}
                        >
                          {e.processingDecision}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
