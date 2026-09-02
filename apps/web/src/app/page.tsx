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
    const fetchTelemetry = async () => {
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

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 2000);
    return () => clearInterval(interval);
  }, []);

  // Compute metrics
  const latestEvent = events[0];
  const avgAnomaly = events.length
    ? (events.reduce((sum, e) => sum + e.anomalyScore, 0) / events.length).toFixed(2)
    : "0.00";
  const avgLatency = events.length
    ? (events.reduce((sum, e) => sum + e.networkLatency, 0) / events.length).toFixed(0)
    : "0";

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 font-sans p-6 md:p-12">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
            EdgeSentinel
          </h1>
          <p className="text-zinc-400 mt-1">Real-time Telemetry & Routing</p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${loading ? 'bg-yellow-500 animate-pulse' : error ? 'bg-red-500' : 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.7)] animate-pulse'}`} />
            <span className="text-sm font-medium text-zinc-400">{loading ? 'Connecting...' : error ? 'Disconnected' : 'Live'}</span>
          </div>
        </div>
      </header>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <MetricCard 
          title="Machine State" 
          value={latestEvent?.machineState || "UNKNOWN"}
          subtitle="Latest reading"
          trend={latestEvent?.machineState === "NORMAL" ? "good" : "bad"}
        />
        <MetricCard 
          title="Avg Anomaly Score" 
          value={avgAnomaly}
          subtitle="Last 50 events"
        />
        <MetricCard 
          title="Avg Latency" 
          value={`${avgLatency}ms`}
          subtitle="Network latency"
        />
        <MetricCard 
          title="Routing" 
          value={latestEvent?.processingDecision || "N/A"}
          subtitle={`Edge CPU: ${latestEvent?.edgeCpu || 0}%`}
          highlight={latestEvent?.processingDecision === "EDGE"}
        />
      </div>

      {/* Main Table */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-sm overflow-hidden shadow-2xl">
        <div className="p-6 border-b border-zinc-800 flex justify-between items-center">
          <h2 className="text-xl font-semibold">Recent Events</h2>
          <span className="text-xs bg-zinc-800 px-3 py-1 rounded-full text-zinc-300 border border-zinc-700">
            {events.length} / 50 payloads
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs uppercase bg-zinc-900/80 text-zinc-400 border-b border-zinc-800">
              <tr>
                <th className="px-6 py-4 font-medium">Time</th>
                <th className="px-6 py-4 font-medium">Device ID</th>
                <th className="px-6 py-4 font-medium">Sensors</th>
                <th className="px-6 py-4 font-medium">Anomaly</th>
                <th className="px-6 py-4 font-medium">Severity</th>
                <th className="px-6 py-4 font-medium">Routing</th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-zinc-500">
                    Waiting for telemetry data...
                  </td>
                </tr>
              ) : (
                events.map((e, idx) => (
                  <tr key={e.eventId || idx} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-zinc-400">
                      {new Date(e.timestamp * 1000).toLocaleTimeString()}
                    </td>
                    <td className="px-6 py-4 text-zinc-300">{e.deviceId}</td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2 text-xs">
                        <span title="Temp">🌡️ {e.temperature.toFixed(1)}</span>
                        <span title="Hum">💧 {e.humidity.toFixed(1)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-mono text-blue-400">
                      {e.anomalyScore.toFixed(3)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                        e.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                        e.severity === 'WARNING' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                        'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      }`}>
                        {e.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded text-xs font-bold tracking-wider ${
                        e.processingDecision === 'EDGE' ? 'bg-indigo-500 text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]' :
                        e.processingDecision === 'CLOUD' ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30' :
                        'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                      }`}>
                        {e.processingDecision}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, subtitle, trend, highlight }: { title: string, value: React.ReactNode, subtitle: string, trend?: "good" | "bad", highlight?: boolean }) {
  return (
    <div className={`p-6 rounded-2xl border ${highlight ? 'border-indigo-500/50 bg-indigo-500/5 shadow-[0_0_15px_rgba(99,102,241,0.15)]' : 'border-zinc-800 bg-zinc-900/50'} backdrop-blur-sm transition-all hover:bg-zinc-800/50`}>
      <h3 className="text-zinc-400 text-sm font-medium mb-2">{title}</h3>
      <div className="flex items-end justify-between">
        <div className={`text-3xl font-bold tracking-tight ${trend === 'bad' ? 'text-red-400' : 'text-zinc-100'}`}>
          {value}
        </div>
      </div>
      <p className="text-zinc-500 text-xs mt-3 font-medium tracking-wide uppercase">{subtitle}</p>
    </div>
  );
}
