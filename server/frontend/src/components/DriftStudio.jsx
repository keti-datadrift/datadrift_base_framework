import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function DriftStudio({ backend, dataset, onBack }) {
  const [datasets, setDatasets] = useState([]);
  const [targetId, setTargetId] = useState("");
  const [drift, setDrift] = useState(null);

  useEffect(() => {
    fetch(`${backend}/datasets`)
      .then((r) => r.json())
      .then(setDatasets);
  }, [backend]);

  const runDrift = () => {
    fetch(`${backend}/drift`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ base_id: dataset.id, target_id: targetId }),
    })
      .then((r) => r.json())
      .then(setDrift);
  };

  const chartData =
    drift?.features?.map((f) => ({
      feature: f.feature,
      value: f.drift_score ?? 0,
    })) ?? [];

  return (
    <div className="max-w-6xl mx-auto">
      <button
        onClick={onBack}
        className="mb-4 px-3 py-2 bg-gray-200 rounded text-xs"
      >
        ← 뒤로
      </button>

      <h2 className="text-xl font-semibold mb-2">🔀 Drift Compare Studio</h2>

      <div className="mb-3 text-sm">
        기준 데이터셋:{" "}
        <span className="font-semibold">{dataset.name}</span>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <select
          className="border rounded px-2 py-1 text-sm"
          onChange={(e) => setTargetId(e.target.value)}
        >
          <option value="">대상 선택</option>
          {datasets
            .filter((d) => d.id !== dataset.id)
            .map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
        </select>
        <button
          onClick={runDrift}
          disabled={!targetId}
          className="px-3 py-2 bg-purple-600 text-white rounded text-xs disabled:bg-gray-300"
        >
          Drift 분석 실행
        </button>
      </div>

      {drift && (
        <>
          <div className="bg-white rounded shadow p-3 mb-4">
            <div className="text-xs text-gray-500">
              Overall share of drifted columns
            </div>
            <div className="text-3xl font-bold text-purple-700">
              {drift.overall.toFixed(3)}
            </div>
          </div>

          <h3 className="text-sm font-semibold mb-1">
            Feature Drift (Evidently 기반)
          </h3>
          <div className="bg-white rounded shadow p-3 h-80 mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <XAxis dataKey="feature" hide />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <h3 className="text-sm font-semibold mb-1">Raw detail</h3>
          <div className="bg-white rounded shadow p-3 h-64 overflow-auto">
            <pre className="text-xs">
              {JSON.stringify(drift.features, null, 2)}
            </pre>
          </div>
        </>
      )}
    </div>
  );
}