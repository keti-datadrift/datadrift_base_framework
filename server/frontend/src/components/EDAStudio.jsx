import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function EDAStudio({ dataset, goBack }) {
  const [eda, setEda] = useState(null);

  useEffect(() => {
    fetch(`http://localhost:8000/eda/${dataset.id}`)
      .then((res) => res.json())
      .then(setEda);
  }, [dataset]);

  if (!eda) return <div>Loading...</div>;

  /*
  const missingChartData = Object.entries(eda.missing_rate).map(([key, val]) => ({
    feature: key,
    value: Number((val * 100).toFixed(2))
  }));
  */
  const missingChartData = Object.entries(eda?.missing_rate ?? {}).map(([key, val]) => ({
    feature: key,
    value: Number((val * 100).toFixed(2)),
  }));

  return (
    <div className="max-w-6xl mx-auto p-4">

      <button onClick={goBack} className="px-3 py-2 bg-gray-200 rounded-lg mb-4">
        ← Back
      </button>

      <h2 className="text-2xl font-bold mb-4">
        🧪 EDA Studio — {dataset.name}
      </h2>

      {/* Shape */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-white shadow rounded-lg">
          <div className="text-gray-500 text-sm">Rows</div>
          <div className="text-2xl font-bold">{eda.shape[0]}</div>
        </div>
        <div className="p-4 bg-white shadow rounded-lg">
          <div className="text-gray-500 text-sm">Columns</div>
          <div className="text-2xl font-bold">{eda.shape[1]}</div>
        </div>
      </div>

      {/* Missing Chart */}
      <h3 className="text-xl font-semibold mb-2">📉 Missing Rate (%)</h3>

      <div className="h-72 bg-white shadow rounded-lg p-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={missingChartData}>
            <XAxis dataKey="feature" hide />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#60a5fa" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Summary */}
      <h3 className="text-xl font-semibold mt-6 mb-2">📊 Summary Statistics</h3>
      <div className="overflow-auto bg-white shadow rounded-lg p-4">
        <pre className="text-sm">{JSON.stringify(eda.summary, null, 2)}</pre>
      </div>

    </div>
  );
}