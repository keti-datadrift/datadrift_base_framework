import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

/**
 * AnalysisPanel - Run and view analysis results with history
 */
export default function AnalysisPanel({ workspaceId, workspaceApi, currentSnapshot }) {
  const [results, setResults] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState({ embedding: false, attributes: false });
  const [error, setError] = useState(null);

  // Load analysis results and history
  const loadResults = useCallback(async () => {
    try {
      setLoading(true);
      const [resultsRes, historyRes] = await Promise.all([
        axios.get(`${workspaceApi}/workspace/${workspaceId}/analysis/results`),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/analysis/history`).catch(() => ({ data: { history: [] } })),
      ]);
      setResults(resultsRes.data.results);
      setHistory(historyRes.data.history || []);
    } catch (err) {
      console.error("Failed to load analysis results:", err);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, workspaceApi]);

  useEffect(() => {
    loadResults();
  }, [loadResults]);

  // Run analysis
  const runAnalysis = async (type) => {
    try {
      setAnalyzing((prev) => ({ ...prev, [type]: true }));
      setError(null);

      await axios.post(
        `${workspaceApi}/workspace/${workspaceId}/analyze/${type}`,
        {},
        { params: { force: true } }
      );

      loadResults();
    } catch (err) {
      console.error(`Failed to run ${type} analysis:`, err);
      setError(`${type} 분석 실패: ${err.message}`);
    } finally {
      setAnalyzing((prev) => ({ ...prev, [type]: false }));
    }
  };

  if (loading) {
    return (
      <div className="p-4 flex items-center justify-center py-12">
        <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="p-4">
      {/* Current snapshot context */}
      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm">
        <span className="text-blue-700">
          📍 분석은 현재 체크아웃된 스냅샷 상태에서 실행됩니다: 
          <strong className="ml-1">{currentSnapshot || "초기 상태"}</strong>
        </span>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* Analysis History - Left column */}
        <div className="col-span-1">
          <h3 className="font-semibold mb-3">📜 분석 히스토리</h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {history.length > 0 ? (
              history.map((item, index) => (
                <div
                  key={item.id || index}
                  className="p-3 bg-white border rounded text-sm hover:border-gray-300 transition"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`w-2 h-2 rounded-full ${
                      item.status === "completed" ? "bg-green-500" : 
                      item.status === "running" ? "bg-blue-500 animate-pulse" : "bg-gray-300"
                    }`}></span>
                    <span className="font-medium capitalize">{item.type}</span>
                  </div>
                  <div className="text-xs text-gray-500">
                    <div>스냅샷: {item.snapshot_context || "workspace"}</div>
                    <div>{new Date(item.timestamp).toLocaleString()}</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-4 text-center text-gray-400 text-sm">
                분석 기록이 없습니다
              </div>
            )}
          </div>
        </div>

        {/* Analysis panels - Right columns */}
        <div className="col-span-2 grid grid-cols-2 gap-4">
        {/* Embedding Analysis */}
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="p-4 border-b bg-gray-50">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">🧠 임베딩 분석</h3>
              <button
                onClick={() => runAnalysis("embedding")}
                disabled={analyzing.embedding}
                className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50"
              >
                {analyzing.embedding ? "분석 중..." : results?.embedding?.status === "available" ? "재분석" : "분석 시작"}
              </button>
            </div>
          </div>
          <div className="p-4">
            {results?.embedding?.status === "available" ? (
              <div>
                <div className="text-sm text-gray-500 mb-2">
                  마지막 분석: {results.embedding.cached_at}
                </div>
                {results.embedding.summary && (
                  <div className="space-y-2">
                    {Object.entries(results.embedding.summary).map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-600">{key}</span>
                        <span className="font-medium">{typeof value === "number" ? value.toFixed(4) : String(value)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">📊</div>
                <div className="text-sm">분석 결과가 없습니다</div>
                <div className="text-xs text-gray-400 mt-1">
                  "분석 시작" 버튼을 클릭하여 임베딩 분석을 실행하세요
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Attribute Analysis */}
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="p-4 border-b bg-gray-50">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">📐 속성 분석</h3>
              <button
                onClick={() => runAnalysis("attributes")}
                disabled={analyzing.attributes}
                className="px-3 py-1 bg-green-500 text-white text-sm rounded hover:bg-green-600 disabled:opacity-50"
              >
                {analyzing.attributes ? "분석 중..." : results?.attributes?.status === "available" ? "재분석" : "분석 시작"}
              </button>
            </div>
          </div>
          <div className="p-4">
            {results?.attributes?.status === "available" ? (
              <div>
                <div className="text-sm text-gray-500 mb-2">
                  마지막 분석: {results.attributes.cached_at}
                </div>
                {results.attributes.summary && (
                  <div className="space-y-2">
                    {Object.entries(results.attributes.summary).map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-600">{key}</span>
                        <span className="font-medium">{typeof value === "number" ? value.toFixed(4) : String(value)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">📏</div>
                <div className="text-sm">분석 결과가 없습니다</div>
                <div className="text-xs text-gray-400 mt-1">
                  "분석 시작" 버튼을 클릭하여 속성 분석을 실행하세요
                </div>
              </div>
            )}
          </div>
          </div>
        </div>
      </div>

      {/* Analysis description */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-medium mb-2">분석 설명</h4>
        <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
          <div>
            <div className="font-medium text-gray-700">임베딩 분석</div>
            <p>DINOv2/CLIP 모델을 사용하여 이미지 임베딩을 추출하고, 분포 특성을 분석합니다.</p>
          </div>
          <div>
            <div className="font-medium text-gray-700">속성 분석</div>
            <p>이미지의 크기, 노이즈 수준, 선명도, 밝기 등 시각적 속성을 분석합니다.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
