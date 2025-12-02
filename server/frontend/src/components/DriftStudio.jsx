import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ComposedChart, Area, Line,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  Cell,
} from "recharts";
import AnalysisProgress from "./AnalysisProgress";

// 상태별 색상
const STATUS_COLORS = {
  NORMAL: { bg: "bg-green-100", text: "text-green-700", border: "border-green-500" },
  WARNING: { bg: "bg-yellow-100", text: "text-yellow-700", border: "border-yellow-500" },
  CRITICAL: { bg: "bg-red-100", text: "text-red-700", border: "border-red-500" },
};

const CHART_COLORS = {
  base: "#3B82F6",
  target: "#EF4444",
  delta: "#F59E0B",
};

export default function DriftStudio({ backend, baseDataset, targetDataset, onBack }) {
  const [loading, setLoading] = useState(true);
  const [drift, setDrift] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [taskId, setTaskId] = useState(null);

  // 비동기 드리프트 분석 시작
  const startDriftAnalysis = useCallback(async () => {
    if (!baseDataset?.id || !targetDataset?.id) return;

    setLoading(true);
    setError(null);

    try {
      // 먼저 비동기 API 시도
      const asyncRes = await fetch(`${backend}/drift/async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_id: baseDataset.id,
          target_id: targetDataset.id,
        }),
      });
      const asyncData = await asyncRes.json();

      if (asyncData.status === 'completed' && asyncData.cached) {
        // 캐시된 결과가 있으면 바로 가져오기
        const res = await axios.post(`${backend}/drift/v2`, {
          base_id: baseDataset.id,
          target_id: targetDataset.id,
        });
        setDrift(res.data);
        setLoading(false);
      } else if (asyncData.status === 'queued' || asyncData.status === 'already_running') {
        // 작업 시작됨 - task ID 저장
        setTaskId(asyncData.task_id);
      } else {
        // 기존 동기 API로 폴백
        const res = await axios.post(`${backend}/drift/v2`, {
          base_id: baseDataset.id,
          target_id: targetDataset.id,
        });
        setDrift(res.data);
        setLoading(false);
      }
    } catch (err) {
      console.error("❌ Drift API Error:", err);
      setError("Drift 분석 중 오류가 발생했습니다.");
      setLoading(false);
    }
  }, [backend, baseDataset, targetDataset]);

  // 분석 완료 핸들러
  const handleDriftComplete = useCallback(async (taskStatus) => {
    setTaskId(null);

    if (taskStatus.status === 'completed') {
      try {
        // 결과 가져오기
        const res = await axios.post(`${backend}/drift/v2`, {
          base_id: baseDataset.id,
          target_id: targetDataset.id,
        });
        setDrift(res.data);
      } catch (err) {
        console.error("❌ Drift 결과 로드 실패:", err);
        setError("Drift 결과를 불러오는 중 오류가 발생했습니다.");
      }
    } else if (taskStatus.status === 'failed') {
      setError(taskStatus.error || "Drift 분석 실패");
    }

    setLoading(false);
  }, [backend, baseDataset, targetDataset]);

  useEffect(() => {
    startDriftAnalysis();
  }, [startDriftAnalysis]);

  if (loading || taskId) {
    return (
      <div className="max-w-6xl mx-auto p-4">
        {onBack && (
          <button onClick={onBack} className="mb-3 px-3 py-2 bg-gray-200 rounded text-xs hover:bg-gray-300">
            ← 뒤로
          </button>
        )}
        
        <h1 className="text-xl font-semibold mb-4">Dataset Drift 분석</h1>

        {/* 메타 정보 */}
        <div className="mb-4 p-4 border rounded bg-gray-50 flex gap-8">
          <div>
            <div className="text-xs text-gray-500">Base</div>
            <div className="font-medium">{baseDataset?.name}</div>
          </div>
          <div className="text-2xl text-gray-300">→</div>
          <div>
            <div className="text-xs text-gray-500">Target</div>
            <div className="font-medium">{targetDataset?.name}</div>
          </div>
        </div>

        {/* 프로그레스 바 */}
        {taskId ? (
          <div className="bg-blue-50 rounded-lg border border-blue-200 p-6">
            <div className="text-center mb-4">
              <div className="text-4xl mb-3">🔄</div>
              <div className="font-semibold text-blue-800 mb-2">드리프트 분석 진행 중</div>
            </div>
            <AnalysisProgress
              backend={backend}
              taskId={taskId}
              taskType="drift"
              onComplete={handleDriftComplete}
              variant="default"
            />
          </div>
        ) : (
          <div className="flex items-center justify-center gap-3 py-8">
            <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
            <span className="text-gray-600">분석 준비 중...</span>
          </div>
        )}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        {onBack && (
          <button onClick={onBack} className="mb-2 px-3 py-2 bg-gray-200 rounded text-xs hover:bg-gray-300">
            ← 뒤로
          </button>
        )}
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  if (!drift) {
    return (
      <div className="p-4">
        {onBack && (
          <button onClick={onBack} className="mb-2 px-3 py-2 bg-gray-200 rounded text-xs hover:bg-gray-300">
            ← 뒤로
          </button>
        )}
        <div className="text-gray-500">데이터 없음</div>
      </div>
    );
  }

  const result = drift.result;
  const type = result?.type;
  const advancedDrift = result?.advanced_drift;
  const hasAdvancedDrift = advancedDrift && advancedDrift.ensemble;

  return (
    <div className="max-w-6xl mx-auto p-4">
      {onBack && (
        <button onClick={onBack} className="mb-3 px-3 py-2 bg-gray-200 rounded text-xs hover:bg-gray-300 transition">
          ← 뒤로
        </button>
      )}

      <h1 className="text-xl font-semibold mb-2">Dataset Drift 분석</h1>

      {/* 메타 정보 */}
      <div className="mb-4 p-4 border rounded bg-gray-50 flex gap-8">
        <div>
          <div className="text-xs text-gray-500">Base</div>
          <div className="font-medium">{drift.meta?.base?.name || baseDataset?.name}</div>
        </div>
        <div className="text-2xl text-gray-300">→</div>
        <div>
          <div className="text-xs text-gray-500">Target</div>
          <div className="font-medium">{drift.meta?.target?.name || targetDataset?.name}</div>
        </div>
      </div>

      {/* 탭 네비게이션 */}
      {hasAdvancedDrift && (
        <div className="flex gap-2 mb-4 border-b">
          <TabButton active={activeTab === "overview"} onClick={() => setActiveTab("overview")}>
            개요
          </TabButton>
          <TabButton active={activeTab === "attributes"} onClick={() => setActiveTab("attributes")}>
            속성 드리프트
          </TabButton>
          <TabButton active={activeTab === "embedding"} onClick={() => setActiveTab("embedding")}>
            임베딩 드리프트
          </TabButton>
          <TabButton active={activeTab === "details"} onClick={() => setActiveTab("details")}>
            상세 정보
          </TabButton>
        </div>
      )}

      {/* ZIP vs ZIP */}
      {type === "zip_zip" && (
        <>
          {activeTab === "overview" && <ZipOverviewTab result={result} advancedDrift={advancedDrift} />}
          {activeTab === "attributes" && advancedDrift && <AttributeDriftTab advancedDrift={advancedDrift} />}
          {activeTab === "embedding" && advancedDrift && <EmbeddingDriftTab advancedDrift={advancedDrift} />}
          {activeTab === "details" && <DetailsTab result={result} advancedDrift={advancedDrift} />}
        </>
      )}

      {/* CSV vs CSV */}
      {type === "csv_csv" && <CSVDriftView result={result} />}

      {/* Unsupported */}
      {type === "unsupported" && (
        <div className="p-4 text-red-500 bg-red-50 rounded">
          ⚠ 이 조합의 Drift 분석은 현재 지원되지 않습니다.
        </div>
      )}
    </div>
  );
}


/* ======================================== */
/* 탭 버튼 */
/* ======================================== */
function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium transition-colors ${
        active
          ? "border-b-2 border-blue-500 text-blue-600"
          : "text-gray-500 hover:text-gray-700"
      }`}
    >
      {children}
    </button>
  );
}


/* ======================================== */
/* ZIP 개요 탭 */
/* ======================================== */
function ZipOverviewTab({ result, advancedDrift }) {
  const ensemble = advancedDrift?.ensemble;
  const status = ensemble?.status || "NORMAL";
  const statusColors = STATUS_COLORS[status] || STATUS_COLORS.NORMAL;

  return (
    <div className="space-y-4">
      {/* 앙상블 드리프트 점수 */}
      {ensemble && (
        <div className={`p-4 rounded border-2 ${statusColors.border} ${statusColors.bg}`}>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-600 mb-1">전체 드리프트 점수</div>
              <div className="text-3xl font-bold">{(ensemble.overall_score * 100).toFixed(1)}%</div>
            </div>
            <div className={`px-4 py-2 rounded-full font-bold ${statusColors.text} ${statusColors.bg}`}>
              {status}
            </div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            임계값: Warning ≥ {(ensemble.thresholds?.warning * 100).toFixed(0)}%, 
            Critical ≥ {(ensemble.thresholds?.critical * 100).toFixed(0)}%
          </div>
        </div>
      )}

      {/* 컴포넌트 점수 레이더 차트 */}
      {ensemble?.component_scores && Object.keys(ensemble.component_scores).length > 0 && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">🎯 드리프트 컴포넌트 점수</div>
          <div className="h-80">
            <ResponsiveContainer>
              <RadarChart data={Object.entries(ensemble.component_scores).map(([key, value]) => ({
                metric: formatMetricName(key),
                score: value * 100,
                fullMark: 100
              }))}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9 }} />
                <Radar
                  name="드리프트 점수"
                  dataKey="score"
                  stroke="#3B82F6"
                  fill="#3B82F6"
                  fillOpacity={0.5}
                />
                <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 기본 ZIP 정보 */}
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-3">📦 ZIP 분석 결과</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="ZIP 타입" value={result.zip_type} />
          {advancedDrift?.file_counts && (
            <>
              <StatCard label="Base 파일 수" value={advancedDrift.file_counts.base} />
              <StatCard label="Target 파일 수" value={advancedDrift.file_counts.target} />
              <StatCard
                label="파일 수 변화"
                value={advancedDrift.file_counts.target - advancedDrift.file_counts.base}
                showDelta
              />
            </>
          )}
        </div>
      </div>

      {/* 스플릿 드리프트 */}
      {result.splits && Object.keys(result.splits).length > 0 && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">📊 스플릿별 변화</div>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={Object.entries(result.splits).map(([name, data]) => ({
                name,
                base: data.base,
                target: data.target,
              }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="base" name="Base" fill={CHART_COLORS.base} />
                <Bar dataKey="target" name="Target" fill={CHART_COLORS.target} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 클래스 분포 드리프트 */}
      {result.classes && Object.keys(result.classes).length > 0 && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">🏷️ 클래스 분포 변화</div>
          <div className="h-80">
            <ResponsiveContainer>
              <BarChart data={Object.entries(result.classes).map(([name, data]) => ({
                name,
                base: data.base,
                target: data.target,
                delta: data.delta,
              }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="base" name="Base" fill={CHART_COLORS.base} />
                <Bar dataKey="target" name="Target" fill={CHART_COLORS.target} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}


/* ======================================== */
/* 속성 드리프트 탭 */
/* ======================================== */
function AttributeDriftTab({ advancedDrift }) {
  const attrDrift = advancedDrift?.attribute_drift;

  if (!attrDrift) {
    return <div className="text-sm text-gray-500">속성 드리프트 데이터가 없습니다.</div>;
  }

  return (
    <div className="space-y-4">
      {/* KL Divergence 점수 */}
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-3">📈 KL Divergence 점수</div>
        <div className="grid grid-cols-3 gap-4">
          {['size', 'noise', 'sharpness'].map((attr) => {
            const data = attrDrift[attr];
            if (!data) return null;
            return (
              <div key={attr} className="p-4 bg-gray-50 rounded">
                <div className="text-xs text-gray-500 mb-1 capitalize">{attr}</div>
                <div className="text-2xl font-bold text-blue-600">
                  {data.kl_divergence?.toFixed(4) || "N/A"}
                </div>
                <div className="mt-2 text-xs text-gray-500">
                  <div>Base: μ={data.base_mean?.toFixed(4)}, σ={data.base_std?.toFixed(4)}</div>
                  <div>Target: μ={data.target_mean?.toFixed(4)}, σ={data.target_std?.toFixed(4)}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 분포 비교 차트들 */}
      {attrDrift.distributions && (
        <>
          {/* 크기 분포 비교 */}
          {attrDrift.distributions.size && (
            <div className="bg-white rounded shadow p-4">
              <div className="font-semibold text-sm mb-3">📏 파일 크기 분포 비교</div>
              <div className="h-64">
                <ResponsiveContainer>
                  <ComposedChart data={attrDrift.distributions.size.bins.map((bin, i) => ({
                    bin: bin.toFixed(3),
                    base: attrDrift.distributions.size.base[i],
                    target: attrDrift.distributions.size.target[i],
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="base" name="Base" fill={CHART_COLORS.base} fillOpacity={0.3} stroke={CHART_COLORS.base} />
                    <Area type="monotone" dataKey="target" name="Target" fill={CHART_COLORS.target} fillOpacity={0.3} stroke={CHART_COLORS.target} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 노이즈 분포 비교 */}
          {attrDrift.distributions.noise && (
            <div className="bg-white rounded shadow p-4">
              <div className="font-semibold text-sm mb-3">🔊 노이즈 레벨 분포 비교</div>
              <div className="h-64">
                <ResponsiveContainer>
                  <ComposedChart data={attrDrift.distributions.noise.bins.map((bin, i) => ({
                    bin: bin.toFixed(3),
                    base: attrDrift.distributions.noise.base[i],
                    target: attrDrift.distributions.noise.target[i],
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="base" name="Base" fill={CHART_COLORS.base} fillOpacity={0.3} stroke={CHART_COLORS.base} />
                    <Area type="monotone" dataKey="target" name="Target" fill={CHART_COLORS.target} fillOpacity={0.3} stroke={CHART_COLORS.target} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 선명도 분포 비교 */}
          {attrDrift.distributions.sharpness && (
            <div className="bg-white rounded shadow p-4">
              <div className="font-semibold text-sm mb-3">🔍 선명도 분포 비교</div>
              <div className="h-64">
                <ResponsiveContainer>
                  <ComposedChart data={attrDrift.distributions.sharpness.bins.map((bin, i) => ({
                    bin: bin.toFixed(3),
                    base: attrDrift.distributions.sharpness.base[i],
                    target: attrDrift.distributions.sharpness.target[i],
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="base" name="Base" fill={CHART_COLORS.base} fillOpacity={0.3} stroke={CHART_COLORS.base} />
                    <Area type="monotone" dataKey="target" name="Target" fill={CHART_COLORS.target} fillOpacity={0.3} stroke={CHART_COLORS.target} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}


/* ======================================== */
/* 임베딩 드리프트 탭 */
/* ======================================== */
function EmbeddingDriftTab({ advancedDrift }) {
  const embDrift = advancedDrift?.embedding_drift;

  if (!embDrift) {
    return <div className="text-sm text-gray-500">임베딩 드리프트 데이터가 없습니다.</div>;
  }

  const metrics = [
    { key: 'mmd', label: 'MMD', description: 'Maximum Mean Discrepancy' },
    { key: 'mean_shift', label: 'Mean Shift', description: '평균 벡터 이동 거리' },
    { key: 'wasserstein', label: 'Wasserstein', description: 'Earth Mover\'s Distance' },
    { key: 'psi', label: 'PSI', description: 'Population Stability Index' },
    { key: 'cosine_distance', label: 'Cosine Distance', description: '코사인 거리' },
  ];

  return (
    <div className="space-y-4">
      {/* 임베딩 메트릭 그리드 */}
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-3">🧠 임베딩 드리프트 메트릭</div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {metrics.map(({ key, label, description }) => {
            const value = embDrift[key];
            if (value === undefined) return null;
            return (
              <div key={key} className="p-4 bg-gray-50 rounded">
                <div className="text-xs text-gray-500 mb-1">{label}</div>
                <div className="text-xl font-bold text-purple-600">{value.toFixed(4)}</div>
                <div className="text-xs text-gray-400 mt-1">{description}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 메트릭 바 차트 */}
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-3">📊 메트릭 비교</div>
        <div className="h-64">
          <ResponsiveContainer>
            <BarChart
              data={metrics
                .filter(m => embDrift[m.key] !== undefined)
                .map(m => ({
                  name: m.label,
                  value: embDrift[m.key],
                }))}
              layout="vertical"
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" domain={[0, 'auto']} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={100} />
              <Tooltip formatter={(value) => value.toFixed(4)} />
              <Bar dataKey="value" fill="#8B5CF6">
                {metrics.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={`hsl(${260 + index * 20}, 70%, 50%)`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* PSI 상세 */}
      {embDrift.psi_max !== undefined && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">📈 PSI 상세</div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded">
              <div className="text-xs text-gray-500 mb-1">평균 PSI</div>
              <div className="text-xl font-bold">{embDrift.psi.toFixed(4)}</div>
            </div>
            <div className="p-4 bg-gray-50 rounded">
              <div className="text-xs text-gray-500 mb-1">최대 PSI</div>
              <div className="text-xl font-bold">{embDrift.psi_max.toFixed(4)}</div>
            </div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            PSI &lt; 0.1: 변화 없음 / 0.1~0.25: 경미한 변화 / &gt; 0.25: 심각한 변화
          </div>
        </div>
      )}
    </div>
  );
}


/* ======================================== */
/* 상세 정보 탭 */
/* ======================================== */
function DetailsTab({ result, advancedDrift }) {
  return (
    <div className="space-y-4">
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-2">📋 기본 드리프트 결과</div>
        <pre className="text-xs overflow-auto bg-gray-50 p-2 rounded max-h-64">
          {JSON.stringify(result, null, 2)}
        </pre>
      </div>

      {advancedDrift && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-2">🔬 고급 드리프트 결과</div>
          <pre className="text-xs overflow-auto bg-gray-50 p-2 rounded max-h-96">
            {JSON.stringify(advancedDrift, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}


/* ======================================== */
/* CSV 드리프트 뷰 */
/* ======================================== */
function CSVDriftView({ result }) {
  const data = result.drift || {};

  return (
    <div className="space-y-4">
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-3">📊 CSV Drift 분석</div>
        <div className="h-64">
          <ResponsiveContainer>
            <BarChart data={Object.entries(data).map(([col, info]) => ({
              name: col,
              delta: info.delta,
            }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="delta" name="Delta (Target - Base)" fill={CHART_COLORS.delta}>
                {Object.entries(data).map(([_, info], index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={info.delta >= 0 ? "#10B981" : "#EF4444"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {Object.entries(data).map(([col, info]) => (
          <div key={col} className="p-4 bg-white rounded shadow">
            <div className="font-semibold text-sm mb-2">{col}</div>
            <div className="text-xs text-gray-600">Base Mean: {info.base_mean}</div>
            <div className="text-xs text-gray-600">Target Mean: {info.target_mean}</div>
            <div className={`text-lg font-bold mt-2 ${info.delta >= 0 ? "text-green-600" : "text-red-600"}`}>
              Δ {info.delta >= 0 ? "+" : ""}{info.delta}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


/* ======================================== */
/* 공통 컴포넌트 */
/* ======================================== */
function StatCard({ label, value, showDelta = false }) {
  let displayValue = value;
  let colorClass = "text-gray-800";

  if (showDelta && typeof value === "number") {
    displayValue = value >= 0 ? `+${value}` : value;
    colorClass = value > 0 ? "text-green-600" : value < 0 ? "text-red-600" : "text-gray-800";
  }

  return (
    <div className="p-3 bg-gray-50 rounded">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-lg font-semibold ${colorClass}`}>{displayValue ?? "-"}</div>
    </div>
  );
}


function formatMetricName(key) {
  const names = {
    'attr_size': '크기',
    'attr_noise': '노이즈',
    'attr_sharpness': '선명도',
    'emb_mmd': 'MMD',
    'emb_mean_shift': 'Mean Shift',
    'emb_wasserstein': 'Wasserstein',
    'emb_psi': 'PSI',
  };
  return names[key] || key;
}
