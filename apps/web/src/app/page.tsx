"use client";

import { useEffect, useState, useRef } from "react";

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

      {/* Main Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left whitespace-nowrap">
            <thead className="text-xs uppercase bg-zinc-900/80 text-zinc-400 border-b border-zinc-800">
              <tr>
                <th className="px-6 py-4 font-semibold tracking-wider">Timestamp</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Device ID</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Severity</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Anomaly Score</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Processing Decision</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-zinc-500">
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

                  return (
                    <tr key={e.eventId || idx} className={rowClasses}>
                      <td className="px-6 py-4 font-mono text-xs text-zinc-400">
                        {new Date(e.timestamp * 1000).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 font-medium text-zinc-200">{e.deviceId}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded text-xs tracking-wide ${severityBadge}`}>
                          {e.severity}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-blue-400">
                        {e.anomalyScore.toFixed(4)}
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

export default function Dashboard() {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Initial fetch for historical data
    const fetchInitialTelemetry = async () => {
      try {
        const res = await fetch("http://localhost:3000/api/v1/telemetry");
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

    // Establish SSE stream
    const sse = new EventSource("http://localhost:3000/api/v1/telemetry/stream");
    
    sse.onmessage = (event) => {
      try {
        const newEvent = JSON.parse(event.data);
        setEvents((prev) => {
          const updated = [newEvent, ...prev];
          if (updated.length > 50) return updated.slice(0, 50);
          return updated;
        });
        setError(null);
      } catch (e) {
        console.error("Error parsing SSE data", e);
      }
    };

    sse.onerror = () => {
      setError("SSE stream disconnected. Reconnecting...");
    };

    return () => {
      sse.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 font-sans p-4 md:p-8">
      <header className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-zinc-100">
            EdgeSentinel Dashboard
          </h1>
          <p className="text-zinc-400 mt-1 text-sm md:text-base">Real-time Telemetry & Routing</p>
        </div>
        <div className="flex items-center space-x-2 bg-zinc-900 px-4 py-2 rounded-lg border border-zinc-800">
          <div className={`w-2.5 h-2.5 rounded-full ${loading ? 'bg-amber-500 animate-pulse' : error ? 'bg-red-500' : 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)] animate-pulse'}`} />
          <span className="text-sm font-medium text-zinc-300">{loading ? 'Connecting...' : error ? 'Disconnected' : 'Live Stream (SSE)'}</span>
        </div>
      </header>

      {/* Main Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left whitespace-nowrap">
            <thead className="text-xs uppercase bg-zinc-900/80 text-zinc-400 border-b border-zinc-800">
              <tr>
                <th className="px-6 py-4 font-semibold tracking-wider">Timestamp</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Device ID</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Severity</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Anomaly Score</th>
                <th className="px-6 py-4 font-semibold tracking-wider">Processing Decision</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-zinc-500">
                    Waiting for telemetry data...
                  </td>
                </tr>
              ) : (
                events.map((e, idx) => {
                  // Strict color-coding logic based on severity
                  let rowClasses = "hover:bg-zinc-800/40 transition-colors";
                  let severityBadge = "";
                  
                  if (e.severity === 'CRITICAL') {
                    rowClasses += " bg-red-950/10";
                    severityBadge = "bg-red-500/20 text-red-500 border border-red-500/30 font-bold";
                  } else if (e.severity === 'WARNING') {
                    severityBadge = "bg-amber-500/20 text-amber-500 border border-amber-500/30 font-semibold";
                  } else {
                    severityBadge = "bg-green-500/10 text-green-400 border border-green-500/20 font-medium";
                  }

                  return (
                    <tr key={e.eventId || idx} className={rowClasses}>
                      <td className="px-6 py-4 font-mono text-xs text-zinc-400">
                        {new Date(e.timestamp * 1000).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 font-medium text-zinc-200">{e.deviceId}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded text-xs tracking-wide ${severityBadge}`}>
                          {e.severity}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-blue-400">
                        {e.anomalyScore.toFixed(4)}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-bold tracking-wider ${
                          e.processingDecision === 'EDGE' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' :
                          e.processingDecision === 'CLOUD' ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30' :
                          'bg-zinc-700/50 text-zinc-300 border border-zinc-600/50'
                        }`}>
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
