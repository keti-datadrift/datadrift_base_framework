import React, { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function DriftStudio({ dataset, goBack }) {
  const [datasets, setDatasets] = useState([]);
  const [targetId, setTargetId] = useState(null);
  const [drift, setDrift] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/datasets")
      .then(res => res.json())
      .then(setDatasets);
  }, []);

  const runDrift = () => {
    fetch("http://localhost:8000/drift", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ base_id: dataset.id, target_id: targetId })
    })
      .then(res => res.json())
      .then(setDrift);
  };

  const chartData = drift?.features?.map(f => ({
    feature: f.feature,
    value: Number(f.drift_score.toFixed(4))
  })) ?? [];

  return (
    <div className="max-w-6xl mx-auto p-4">

      <button onClick={goBack} className="px-3 py-2 bg-gray-200 rounded-lg mb-4">
        ← Back
      </button>

      <h2 className="text-2xl font-bold mb-4">🔀 Drift Compare Studio</h2>

      <p className="text-lg mb-2">
        기준 데이터셋: <b>{dataset.name}</b>
      </p>

      <select
        onChange={(e) => setTargetId(e.target.value)}
        className="border p-2 rounded-lg mb-4"
      >
        <option>대상 데이터셋 선택</option>
        {datasets.filter(d => d.id !== dataset.id).map(d => (
          <option key={d.id} value={d.id}>{d.name}</option>
        ))}
      </select>

      <button
        onClick={runDrift}
        disabled={!targetId}
        className="px-4 py-2 bg-purple-600 text-white rounded-lg mb-6 disabled:bg-gray-300"
      >
        Compare Drift
      </button>

      {drift && (
        <>
          {/* Overall Drift */}
          <div className="p-4 bg-white shadow rounded-lg mb-6">
            <div className="text-gray-600">Overall Drift Score</div>
            <div className="text-3xl font-bold text-purple-600">
              {drift.overall_drift.toFixed(4)}
            </div>
          </div>

          {/* Feature Drift Chart */}
          <h3 className="text-xl font-semibold mb-2">📊 Feature Drift</h3>

          <div className="h-80 bg-white shadow rounded-lg p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <XAxis dataKey="feature" hide />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#c084fc" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Raw Debug Info */}
          <h3 className="text-xl font-semibold mt-6 mb-2">Detail Data</h3>
          <div className="bg-white shadow rounded-lg p-4">
            <pre className="text-sm">{JSON.stringify(drift.features, null, 2)}</pre>
          </div>
        </>
      )}
    </div>
  );
}