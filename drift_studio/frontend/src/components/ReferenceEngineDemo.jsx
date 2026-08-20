import React, { useState } from "react";
import axios from "axios";

const STATUS_STYLES = {
  alert: { bg: "bg-red-100", text: "text-red-700", border: "border-red-500", label: "ALERT" },
  quiet: { bg: "bg-green-100", text: "text-green-700", border: "border-green-500", label: "QUIET" },
  deferred: { bg: "bg-gray-100", text: "text-gray-700", border: "border-gray-400", label: "DEFERRED" },
};

const LEVEL_ORDER = [
  "L0_고정기준선",
  "L1_전년동일병기",
  "L2_레짐재정의",
  "L3_계절분해",
  "L4_개입보정",
];

const LEVEL_LABELS = {
  L0_고정기준선: "L0 · Fixed Baseline",
  L1_전년동일병기: "L1 · Year-over-Year Dual Basis",
  L2_레짐재정의: "L2 · Regime Redefinition",
  L3_계절분해: "L3 · STL Seasonal Decomposition",
  L4_개입보정: "L4 · Intervention-Adjusted",
};

function LevelCard({ levelKey, level }) {
  if (!level) {
    return (
      <div className="border rounded-lg p-3 bg-gray-50 border-gray-200 text-xs text-gray-400">
        {LEVEL_LABELS[levelKey] || levelKey} — no data
      </div>
    );
  }
  const s = STATUS_STYLES[level.status] || STATUS_STYLES.deferred;
  return (
    <div className={`border rounded-lg p-3 ${s.bg} ${s.border}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-sm text-gray-800">{LEVEL_LABELS[levelKey] || levelKey}</span>
        <span className={`px-2 py-0.5 rounded text-xs font-bold border ${s.text} ${s.border} bg-white`}>
          {s.label}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-gray-700 mb-2">
        <div><span className="text-gray-500">expected: </span>{level.expected ?? "—"}</div>
        <div><span className="text-gray-500">actual: </span>{level.actual ?? "—"}</div>
        <div><span className="text-gray-500">z-score: </span>{level.z_score ?? "—"}</div>
      </div>
      <div className="text-xs text-gray-600 italic">{level.reason}</div>
      {level.attribution_confidence != null && (
        <div className="text-xs text-gray-500 mt-1">
          attribution confidence: {level.attribution_confidence}
        </div>
      )}
    </div>
  );
}

function ColumnCard({ columnKey, columnResult }) {
  return (
    <div className="bg-white border rounded-lg shadow-sm p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-lg text-gray-900">{columnKey}</h3>
        <span className="text-xs text-gray-500">
          window: {columnResult.evaluation_window?.start} → {columnResult.evaluation_window?.end}
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {LEVEL_ORDER.map((levelKey) => (
          <LevelCard key={levelKey} levelKey={levelKey} level={columnResult.levels?.[levelKey]} />
        ))}
      </div>
    </div>
  );
}

export default function ReferenceEngineDemo({ backend }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const runDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${backend}/reference-engine/demo`);
      setResult(res.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message =
        typeof detail === "string" ? detail : detail ? JSON.stringify(detail, null, 2) : err.message;
      setError(message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const columns = result?.results ? Object.entries(result.results) : [];
  const newEvents = result?.new_candidate_events || [];
  const pendingEvents = result?.pending_candidate_events || [];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1 text-gray-900">Reference-Engine Ladder Demo</h1>
        <p className="text-sm text-gray-500">
          Runs <code>ddoc analyze drift --detector reference_engine</code> against a committed
          toy fixture (2 columns, ~3 years of daily data) and shows the level0–4 ladder's raw
          output. Every click is a live subprocess call — nothing here is cached or pre-computed.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          이 데모는 개입/레짐 이벤트를 미리 등록하지 않았습니다 — 그래서 L2는 L0과, L4는 L3와 같은 값을
          보이는 게 정상입니다(등록된 이벤트가 없으면 상위 레벨과 동일하게 판단).
        </p>
      </div>

      <button
        onClick={runDemo}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 font-medium"
      >
        {loading && (
          <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
        )}
        {loading ? "Running ladder…" : "Run reference-engine demo"}
      </button>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm whitespace-pre-wrap">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 space-y-6">
          <div className="flex flex-wrap items-center gap-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Overall Score</div>
              <div className="text-2xl font-bold text-blue-700">{result.overall_score}</div>
            </div>
            <div className="text-xs text-gray-500">
              status: {result.status} · backend: {result.backend} · detector: {result.detector} · method:{" "}
              {result.method}
            </div>
          </div>

          {columns.map(([columnKey, columnResult]) => (
            <ColumnCard key={columnKey} columnKey={columnKey} columnResult={columnResult} />
          ))}

          <div className="bg-white border rounded-lg p-4">
            <h3 className="font-semibold mb-2 text-gray-900">Event Ontology — Auto-Detected Candidates</h3>
            <p className="text-xs text-gray-500 mb-3">
              Candidate events are proposed automatically when a single day deviates &gt;5σ from
              its trailing 30-day window (stricter than the ladder's own 3.0σ threshold) and stay
              unconfirmed until a human approves them.
            </p>
            {newEvents.length === 0 && pendingEvents.length === 0 && (
              <div className="text-xs text-gray-400">
                No candidate events this run. (If you've already clicked "Run demo" before, the
                revenue column's step-change may already be logged from that earlier run —
                new_candidate_events only lists newly-proposed events, not previously-seen ones.)
              </div>
            )}
            {newEvents.length > 0 && (
              <div className="mb-3">
                <div className="text-xs text-gray-500 mb-1">
                  newly proposed this run ({newEvents.length}):
                </div>
                <div className="flex flex-wrap gap-2">
                  {newEvents.map((eventId) => (
                    <span key={eventId} className="font-mono text-xs bg-gray-50 px-2 py-1 rounded border">
                      {eventId}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {pendingEvents.length > 0 && (
              <div>
                <div className="text-xs text-gray-500 mb-1">all pending review ({pendingEvents.length}):</div>
                <table className="text-xs w-full border-collapse">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-1 pr-2">series</th>
                      <th className="py-1 pr-2">type</th>
                      <th className="py-1 pr-2">start</th>
                      <th className="py-1 pr-2">description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingEvents.map((ev) => (
                      <tr key={ev.event_id} className="border-b border-gray-100">
                        <td className="py-1 pr-2 font-mono">{ev.series}</td>
                        <td className="py-1 pr-2">{ev.event_type}</td>
                        <td className="py-1 pr-2">{ev.start}</td>
                        <td className="py-1 pr-2">{ev.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
