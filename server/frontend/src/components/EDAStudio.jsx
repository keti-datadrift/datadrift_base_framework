import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function EDAStudio({ backend, dataset, onBack }) {
  const [eda, setEda] = useState(null);

  useEffect(() => {
    fetch(`${backend}/eda/${dataset.id}`)
      .then((r) => r.json())
      .then(setEda)
      .catch((e) => console.error("EDA fetch failed", e));
  }, [backend, dataset]);

  if (!eda) return <div className="p-4">로딩중...</div>;

  const missingChartData = Object.entries(eda.missing_rate ?? {}).map(
    ([k, v]) => ({
      feature: k,
      value: Number((v * 100).toFixed(2)),
    })
  );

  const type = eda.type || dataset.type;

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <button
        onClick={onBack}
        className="mb-2 px-3 py-2 bg-gray-200 rounded text-xs"
      >
        ← 뒤로
      </button>

      <h2 className="text-xl font-semibold">
        🧪 EDA Studio — {dataset.name}
      </h2>

      <div className="grid grid-cols-3 gap-4 mb-2">
        <div className="bg-white rounded shadow p-3">
          <div className="text-xs text-gray-500">Rows</div>
          <div className="text-2xl font-bold">{eda.shape[0]}</div>
        </div>
        <div className="bg-white rounded shadow p-3">
          <div className="text-xs text-gray-500">Columns</div>
          <div className="text-2xl font-bold">{eda.shape[1]}</div>
        </div>
        <div className="bg-white rounded shadow p-3">
          <div className="text-xs text-gray-500">Type</div>
          <div className="text-lg font-semibold uppercase">{type}</div>
        </div>
      </div>

      {type === "csv" && missingChartData.length > 0 && (
        <>
          <h3 className="text-sm font-semibold mb-1">Missing Rate (%)</h3>
          <div className="bg-white rounded shadow p-3 h-72 mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={missingChartData}>
                <XAxis dataKey="feature" hide />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {type === "text" && eda.preview && (
        <div className="bg-white rounded shadow p-3">
          <h3 className="text-sm font-semibold mb-1">Text Preview</h3>
          <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-64 whitespace-pre-wrap">
            {eda.preview.join("\n")}
          </pre>
        </div>
      )}

      <h3 className="text-sm font-semibold mb-1">Summary</h3>
      <div className="bg-white rounded shadow p-3 h-64 overflow-auto">
        <pre className="text-xs">
          {JSON.stringify(eda.summary, null, 2)}
        </pre>
      </div>
    </div>
  );
}
