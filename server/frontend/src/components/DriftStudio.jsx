import React, { useEffect, useState } from "react";
import axios from "axios";
import { Bar } from "react-chartjs-2";

export default function DriftStudio({ baseId, targetId }) {
  const [loading, setLoading] = useState(true);
  const [drift, setDrift] = useState(null);
  const [error, setError] = useState(null);

  console.log("DriftStudio Props:", { baseId, targetId });

  useEffect(() => {
    if (!baseId || !targetId) return;

    setLoading(true);
    axios
      .post("http://localhost:8000/drift/v2", {
        base_id: baseId,
        target_id: targetId,
      })
      .then((res) => {
        console.log("🔥 Drift API Response:", res.data);
        setDrift(res.data);
        setError(null);
      })
      .catch((err) => {
        console.error("❌ Drift API Error:", err);
        setError("Drift 분석 중 오류가 발생했습니다.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [baseId, targetId]);

  if (loading) return <div className="p-4">⏳ Drift 분석 중...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;
  if (!drift) return <div className="p-4">데이터 없음</div>;

  const result = drift.result; // 핵심 데이터
  const type = result?.type;

  // ----------------------------------------
  // ZIP vs ZIP UI
  // ----------------------------------------
  const renderZipDrift = () => {
    const splits = result.splits || {};
    const classes = result.classes || {};
    const summary = result.summary || {};

    return (
      <div className="p-4 space-y-6">
        {/* ZIP TYPE */}
        <div className="text-xl font-bold">
          ZIP Drift 분석 (Format: {result.zip_type})
        </div>

        {/* Summary */}
        <div className="grid grid-cols-3 gap-4">
          {Object.entries(summary).map(([k, v]) => (
            <div key={k} className="p-3 border rounded bg-gray-50">
              <div className="text-xs text-gray-500">{k}</div>
              <div className="text-lg font-semibold">{v}</div>
            </div>
          ))}
        </div>

        {/* Splits */}
        {Object.keys(splits).length > 0 && (
          <div>
            <div className="text-lg font-bold mb-2">Data Splits Drift</div>
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(splits).map(([name, s]) => (
                <div key={name} className="p-3 border rounded bg-gray-50">
                  <div className="font-bold">{name}</div>
                  <div>Base: {s.base}</div>
                  <div>Target: {s.target}</div>
                  <div className="font-semibold text-blue-600">
                    Δ {s.delta >= 0 ? "+" : ""}
                    {s.delta}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Class Drift */}
        {Object.keys(classes).length > 0 && (
          <div>
            <div className="text-lg font-bold mb-2">Class Distribution Drift</div>

            <Bar
              data={{
                labels: Object.keys(classes),
                datasets: [
                  {
                    label: "Base",
                    data: Object.values(classes).map((c) => c.base),
                    backgroundColor: "rgba(54, 162, 235, 0.6)",
                  },
                  {
                    label: "Target",
                    data: Object.values(classes).map((c) => c.target),
                    backgroundColor: "rgba(255, 99, 132, 0.6)",
                  },
                ],
              }}
            />
          </div>
        )}
      </div>
    );
  };

  // ----------------------------------------
  // CSV vs CSV UI
  // ----------------------------------------
  const renderCsvDrift = () => {
    const data = result.drift || {};

    return (
      <div className="p-4 space-y-6">
        <div className="text-xl font-bold">CSV Drift 분석</div>

        <Bar
          data={{
            labels: Object.keys(data),
            datasets: [
              {
                label: "Delta (target - base)",
                data: Object.values(data).map((x) => x.delta),
                backgroundColor: "rgba(255, 159, 64, 0.6)",
              },
            ],
          }}
        />

        <div className="grid grid-cols-3 gap-4">
          {Object.entries(data).map(([col, info]) => (
            <div key={col} className="p-3 border rounded bg-white shadow">
              <div className="font-bold">{col}</div>
              <div className="text-sm">Base Mean: {info.base_mean}</div>
              <div className="text-sm">Target Mean: {info.target_mean}</div>
              <div className="font-semibold mt-1 text-blue-700">
                Δ {info.delta}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // ----------------------------------------
  // Unsupported
  // ----------------------------------------
  const renderUnsupported = () => (
    <div className="p-4 text-red-500">
      ⚠ 이 조합의 Drift 분석은 현재 지원되지 않습니다.
    </div>
  );

  // ----------------------------------------
  // Main Branch Rendering
  // ----------------------------------------
  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Dataset Drift 비교 결과</h1>

      {/* 공통 추가 정보 */}
      <div className="mb-6 p-4 border rounded bg-gray-50">
        <div className="text-sm text-gray-600">Base: {drift.meta.base.name}</div>
        <div className="text-sm text-gray-600">Target: {drift.meta.target.name}</div>
      </div>

      {type === "zip_zip" && renderZipDrift()}
      {type === "csv_csv" && renderCsvDrift()}
      {type === "unsupported" && renderUnsupported()}
    </div>
  );
}