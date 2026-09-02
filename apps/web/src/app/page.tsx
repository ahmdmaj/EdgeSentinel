"use client";

import { useEffect, useState } from "react";

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
