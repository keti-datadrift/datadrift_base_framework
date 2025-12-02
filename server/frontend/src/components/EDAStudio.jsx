import React, { useEffect, useState, useCallback } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
  ScatterChart, Scatter,
  LineChart, Line,
} from "recharts";
import AnalysisProgress from "./AnalysisProgress";
import { useTaskWebSocket } from "../hooks/useTaskWebSocket";

// 차트 색상
const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'];

export default function EDAStudio({ backend, dataset, onBack }) {
  // 기본 EDA 데이터 (구조 + 클래스)
  const [eda, setEda] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // 초기 상태 체크 완료 여부 (진행 중인 작업 확인)
  const [initialCheckDone, setInitialCheckDone] = useState(false);
  
  // 심화 분석 데이터 (별도 로딩)
  const [imageAnalysis, setImageAnalysis] = useState(null);
  const [imageAnalysisLoading, setImageAnalysisLoading] = useState(false);
  const [imageAnalysisLoaded, setImageAnalysisLoaded] = useState(false);
  const [imageAnalysisTaskId, setImageAnalysisTaskId] = useState(null);
  
  const [clustering, setClustering] = useState(null);
  const [clusteringLoading, setClusteringLoading] = useState(false);
  const [clusteringLoaded, setClusteringLoaded] = useState(false);
  const [clusteringTaskId, setClusteringTaskId] = useState(null);
  
  const [activeTab, setActiveTab] = useState("overview");

  // 기본 EDA 로드 (구조 + 클래스만)
  useEffect(() => {
    setLoading(true);
    fetch(`${backend}/eda/${dataset.id}`)
      .then((r) => r.json())
      .then((data) => {
        setEda(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("EDA 로딩 실패:", err);
        setLoading(false);
      });
  }, [backend, dataset]);

  // 컴포넌트 마운트 시 진행 중인 작업 및 캐시 여부 확인 (빠른 체크)
  useEffect(() => {
    let isMounted = true;
    
    const checkInitialStatus = async () => {
      try {
        // /status API만 호출 (캐시 여부 포함, 분석 수행 없음)
        const statusRes = await fetch(`${backend}/eda/${dataset.id}/status`);
        if (!statusRes.ok || !isMounted) return;
        
        const statusData = await statusRes.json();
        
        // 1. 진행 중인 작업 확인
        for (const task of statusData.running_tasks || []) {
          if (task.task_type === 'image_analysis') {
            setImageAnalysisTaskId(task.task_id);
            setImageAnalysisLoading(true);
          }
          if (task.task_type === 'clustering') {
            setClusteringTaskId(task.task_id);
            setClusteringLoading(true);
          }
        }
        
        // 2. 캐시된 데이터가 있으면 loaded 표시 + 백그라운드에서 데이터 로드
        const cacheStatus = statusData.cache_status || {};
        const hasRunningImageAnalysis = statusData.running_tasks?.some(t => t.task_type === 'image_analysis');
        const hasRunningClustering = statusData.running_tasks?.some(t => t.task_type === 'clustering');
        
        if (cacheStatus.image_analysis && !hasRunningImageAnalysis) {
          // 캐시가 있으면 즉시 loaded 표시
          setImageAnalysisLoaded(true);
          // 백그라운드에서 실제 데이터 로드
          fetch(`${backend}/eda/${dataset.id}/image-analysis`)
            .then(res => res.ok ? res.json() : null)
            .then(data => {
              if (isMounted && data && !data.error && data.num_images) {
                setImageAnalysis(data);
              }
            })
            .catch(() => {});
        }
        
        if (cacheStatus.clustering && !hasRunningClustering) {
          // 캐시가 있으면 즉시 loaded 표시
          setClusteringLoaded(true);
          // 백그라운드에서 실제 데이터 로드
          fetch(`${backend}/eda/${dataset.id}/clustering`)
            .then(res => res.ok ? res.json() : null)
            .then(data => {
              if (isMounted && data && !data.error && data.n_clusters) {
                setClustering(data);
              }
            })
            .catch(() => {});
        }
        
        // UI 빨리 표시
        setInitialCheckDone(true);
      } catch (err) {
        console.error("초기 상태 확인 실패:", err);
        if (isMounted) {
          setInitialCheckDone(true);
        }
      }
    };
    
    checkInitialStatus();
    
    return () => {
      isMounted = false;
    };
  }, [backend, dataset.id]);

  // 이미지 속성 분석 로드 (비동기)
  const loadImageAnalysis = useCallback(async (force = false) => {
    // 재분석이 아닌 경우, 이미 로드되었거나 로딩 중이면 스킵
    if (!force && (imageAnalysisLoaded || imageAnalysisLoading)) return;
    
    setImageAnalysisLoading(true);
    
    try {
      // 비동기 API 호출 (force 파라미터 전달)
      const url = force 
        ? `${backend}/eda/async/${dataset.id}/image-analysis?force=true`
        : `${backend}/eda/async/${dataset.id}/image-analysis`;
      
      const res = await fetch(url, {
        method: 'POST',
      });
      const data = await res.json();
      
      if (data.status === 'completed' && data.cached && !force) {
        // 캐시된 결과가 있으면 바로 가져오기 (재분석이 아닌 경우만)
        const analysisRes = await fetch(`${backend}/eda/${dataset.id}/image-analysis`);
        const analysisData = await analysisRes.json();
        setImageAnalysis(analysisData);
        setImageAnalysisLoaded(true);
        setImageAnalysisLoading(false);
      } else if (data.status === 'queued' || data.status === 'already_running') {
        // 작업 시작됨 - task ID 저장
        setImageAnalysisTaskId(data.task_id);
      } else {
        console.error("이미지 분석 요청 실패:", data.message);
        setImageAnalysisLoading(false);
      }
    } catch (err) {
      console.error("이미지 분석 요청 오류:", err);
      setImageAnalysisLoading(false);
    }
  }, [backend, dataset.id, imageAnalysisLoaded, imageAnalysisLoading]);

  // 이미지 분석 완료 핸들러
  const handleImageAnalysisComplete = useCallback(async (taskStatus) => {
    setImageAnalysisTaskId(null);
    
    if (taskStatus.status === 'completed') {
      // 결과 가져오기
      try {
        const res = await fetch(`${backend}/eda/${dataset.id}/image-analysis`);
        const data = await res.json();
        if (!data.error) {
          setImageAnalysis(data);
        }
      } catch (err) {
        console.error("이미지 분석 결과 로드 실패:", err);
      }
    }
    
    setImageAnalysisLoaded(true);
    setImageAnalysisLoading(false);
  }, [backend, dataset.id]);

  // 클러스터링 분석 로드 (비동기)
  const loadClustering = useCallback(async (force = false) => {
    // 재분석이 아닌 경우, 이미 로드되었거나 로딩 중이면 스킵
    if (!force && (clusteringLoaded || clusteringLoading)) return;
    
    setClusteringLoading(true);
    
    try {
      // 비동기 API 호출 (force 파라미터 전달)
      const url = force
        ? `${backend}/eda/async/${dataset.id}/clustering?force=true`
        : `${backend}/eda/async/${dataset.id}/clustering`;
      
      const res = await fetch(url, {
        method: 'POST',
      });
      const data = await res.json();
      
      if (data.status === 'completed' && data.cached && !force) {
        // 캐시된 결과가 있으면 바로 가져오기 (재분석이 아닌 경우만)
        const clusteringRes = await fetch(`${backend}/eda/${dataset.id}/clustering`);
        const clusteringData = await clusteringRes.json();
        setClustering(clusteringData);
        setClusteringLoaded(true);
        setClusteringLoading(false);
      } else if (data.status === 'queued' || data.status === 'already_running') {
        // 작업 시작됨 - task ID 저장
        setClusteringTaskId(data.task_id);
      } else {
        console.error("클러스터링 요청 실패:", data.message);
        setClusteringLoading(false);
      }
    } catch (err) {
      console.error("클러스터링 요청 오류:", err);
      setClusteringLoading(false);
    }
  }, [backend, dataset.id, clusteringLoaded, clusteringLoading]);

  // 클러스터링 완료 핸들러
  const handleClusteringComplete = useCallback(async (taskStatus) => {
    setClusteringTaskId(null);
    
    if (taskStatus.status === 'completed') {
      // 결과 가져오기
      try {
        const res = await fetch(`${backend}/eda/${dataset.id}/clustering`);
        const data = await res.json();
        if (!data.error) {
          setClustering(data);
        }
      } catch (err) {
        console.error("클러스터링 결과 로드 실패:", err);
      }
    }
    
    setClusteringLoaded(true);
    setClusteringLoading(false);
  }, [backend, dataset.id]);

  // 탭 변경 시 해당 데이터 로드
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    
    if (tab === "distributions" && !imageAnalysisLoaded) {
      loadImageAnalysis();
    } else if (tab === "clustering" && !clusteringLoaded) {
      loadClustering();
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-4">
        <button onClick={onBack} className="mb-2 px-3 py-2 bg-gray-200 rounded text-xs hover:bg-gray-300">
          ← 뒤로
        </button>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
          EDA 분석 중...
        </div>
      </div>
    );
  }

  if (!eda) {
    return (
      <div className="max-w-6xl mx-auto p-4">
        <button onClick={onBack} className="mb-2 px-3 py-2 bg-gray-200 rounded text-xs hover:bg-gray-300">
          ← 뒤로
        </button>
        <div className="text-sm text-red-500">EDA 데이터를 불러올 수 없습니다.</div>
      </div>
    );
  }

  const type = eda.type || dataset.type;

  return (
    <div className="max-w-6xl mx-auto p-4">
      <button onClick={onBack} className="mb-3 px-3 py-2 bg-gray-200 rounded text-xs hover:bg-gray-300 transition">
        ← 뒤로
      </button>

      <div className="mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          📊 EDA Studio — {dataset.name}
        </h2>
        <div className="text-xs text-gray-500">Type: {type}</div>
      </div>

      {/* 탭 네비게이션 (ZIP 타입일 때만) */}
      {type === "zip" && (
        <div className="flex gap-1 mb-4 bg-gray-100 p-1 rounded-lg">
          <TabButton 
            active={activeTab === "overview"} 
            onClick={() => handleTabChange("overview")}
            icon="📦"
          >
            개요
          </TabButton>
          <TabButton 
            active={activeTab === "distributions"} 
            onClick={() => handleTabChange("distributions")}
            icon="📈"
            loading={imageAnalysisLoading}
          >
            분포 분석
          </TabButton>
          <TabButton 
            active={activeTab === "clustering"} 
            onClick={() => handleTabChange("clustering")}
            icon="🧠"
            loading={clusteringLoading}
          >
            임베딩 분석
          </TabButton>
          <TabButton 
            active={activeTab === "details"} 
            onClick={() => handleTabChange("details")}
            icon="📋"
          >
            상세 정보
          </TabButton>
        </div>
      )}

      {/* CSV 뷰 */}
      {type === "csv" && <CSVView eda={eda} />}

      {/* TEXT 뷰 */}
      {type === "text" && <TextView eda={eda} />}

      {/* ZIP 뷰 */}
      {type === "zip" && (
        <>
          {activeTab === "overview" && (
            <ZipOverviewTab 
              eda={eda} 
              imageAnalysis={imageAnalysis}
              onLoadImageAnalysis={loadImageAnalysis}
              imageAnalysisLoading={imageAnalysisLoading}
              imageAnalysisLoaded={imageAnalysisLoaded}
              imageAnalysisTaskId={imageAnalysisTaskId}
              backend={backend}
              onImageAnalysisComplete={handleImageAnalysisComplete}
              initialCheckDone={initialCheckDone}
              // 클러스터링 상태 추가
              clustering={clustering}
              onLoadClustering={loadClustering}
              clusteringLoading={clusteringLoading}
              clusteringLoaded={clusteringLoaded}
              clusteringTaskId={clusteringTaskId}
              onClusteringComplete={handleClusteringComplete}
            />
          )}
          {activeTab === "distributions" && (
            <DistributionsTab 
              imageAnalysis={imageAnalysis} 
              loading={imageAnalysisLoading}
              loaded={imageAnalysisLoaded}
              onLoad={loadImageAnalysis}
              taskId={imageAnalysisTaskId}
              backend={backend}
              onComplete={handleImageAnalysisComplete}
            />
          )}
          {activeTab === "clustering" && (
            <ClusteringTab 
              clustering={clustering} 
              loading={clusteringLoading}
              loaded={clusteringLoaded}
              onLoad={loadClustering}
              taskId={clusteringTaskId}
              backend={backend}
              onComplete={handleClusteringComplete}
              initialCheckDone={initialCheckDone}
            />
          )}
          {activeTab === "details" && (
            <DetailsTab 
              eda={eda} 
              imageAnalysis={imageAnalysis}
            />
          )}
        </>
      )}

      {/* FALLBACK */}
      {!["csv", "text", "zip"].includes(type) && (
        <div className="bg-white rounded shadow p-3">
          <div className="font-semibold text-sm mb-2">EDA 결과</div>
          <pre className="text-xs overflow-auto">{JSON.stringify(eda, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}


/* ======================================== */
/* 탭 버튼 컴포넌트 */
/* ======================================== */
function TabButton({ active, onClick, children, icon, loading }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2 ${
        active
          ? "bg-white text-blue-600 shadow-sm"
          : "text-gray-600 hover:text-gray-800 hover:bg-gray-200"
      }`}
    >
      {loading ? (
        <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      ) : (
        <span>{icon}</span>
      )}
      {children}
    </button>
  );
}


/* ======================================== */
/* CSV 뷰 */
/* ======================================== */
function CSVView({ eda }) {
  return (
    <div className="space-y-4">
      {eda.shape && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-2">📊 데이터 형태</div>
          <div className="grid grid-cols-2 gap-4">
            <StatCard label="행 (Rows)" value={eda.shape[0].toLocaleString()} />
            <StatCard label="열 (Columns)" value={eda.shape[1]} />
          </div>
        </div>
      )}

      {eda.missing_rate && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-2">🔍 결측률</div>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(eda.missing_rate).map(([col, rate]) => (
              <div key={col} className="text-xs p-2 bg-gray-50 rounded">
                <div className="font-medium truncate">{col}</div>
                <div className={rate > 0.1 ? "text-red-500" : "text-green-600"}>
                  {(rate * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {eda.summary && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-2">📈 통계 요약</div>
          <pre className="text-xs overflow-auto bg-gray-50 p-2 rounded">
            {JSON.stringify(eda.summary, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}


/* ======================================== */
/* TEXT 뷰 */
/* ======================================== */
function TextView({ eda }) {
  return (
    <div className="space-y-4">
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-2">📝 텍스트 통계</div>
        <div className="grid grid-cols-2 gap-4">
          <StatCard label="총 라인 수" value={eda.num_lines?.toLocaleString()} />
          <StatCard label="평균 라인 길이" value={eda.avg_line_length?.toFixed(2)} />
        </div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-2">미리보기 (상위 20줄)</div>
        <pre className="text-xs whitespace-pre-wrap bg-gray-50 p-2 rounded max-h-96 overflow-auto">
          {(eda.preview || eda.first_lines || []).join("\n")}
        </pre>
      </div>
    </div>
  );
}


/* ======================================== */
/* ZIP 개요 탭 */
/* ======================================== */
function ZipOverviewTab({ 
  eda, 
  imageAnalysis, 
  onLoadImageAnalysis, 
  imageAnalysisLoading, 
  imageAnalysisLoaded,
  imageAnalysisTaskId,
  backend,
  onImageAnalysisComplete,
  initialCheckDone = true,
  // 클러스터링 상태
  clustering,
  onLoadClustering,
  clusteringLoading,
  clusteringLoaded,
  clusteringTaskId,
  onClusteringComplete,
}) {
  const summary = imageAnalysis?.summary;

  return (
    <div className="space-y-4">
      {/* 기본 정보 */}
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-3">📦 데이터셋 개요</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="ZIP 타입" value={eda.zip_type} />
          <StatCard label="총 파일" value={eda.stats?.total_files?.toLocaleString()} />
          <StatCard label="이미지 파일" value={eda.stats?.image_files?.toLocaleString()} />
          <StatCard label="라벨 파일" value={eda.stats?.text_files?.toLocaleString()} />
        </div>
      </div>

      {/* 이미지 분석 요약 (로드된 경우) */}
      {summary && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">🖼️ 이미지 분석 요약</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="분석된 이미지" value={summary.total_images} />
            <StatCard label="총 크기" value={`${summary.total_size_mb?.toFixed(2)} MB`} />
            <StatCard label="평균 크기" value={`${summary.avg_size_mb?.toFixed(3)} MB`} />
            <StatCard label="포맷 수" value={Object.keys(summary.formats || {}).length} />
          </div>
        </div>
      )}

      {/* 이미지 분석 상태 표시 */}
      
      {/* 0. 초기 상태 확인 중 */}
      {!initialCheckDone && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="animate-spin h-5 w-5 border-2 border-gray-400 border-t-transparent rounded-full"></div>
            <div>
              <div className="font-semibold text-sm text-gray-700">분석 상태 확인 중...</div>
              <div className="text-xs text-gray-500">잠시만 기다려주세요.</div>
            </div>
          </div>
        </div>
      )}
      
      {/* ====== 심화 분석 상태 카드 (이미지 속성 분석 + 임베딩 분석) ====== */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="font-semibold text-sm mb-3">🔬 심화 분석 상태</div>
        <div className="space-y-3">
          
          {/* ----- 이미지 속성 분석 상태 ----- */}
          {/* 초기 확인 중 */}
          {!initialCheckDone && (
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full"></div>
                <span className="text-sm text-gray-600">상태 확인 중...</span>
              </div>
            </div>
          )}
          
          {/* 이미지 속성 분석 완료 */}
          {initialCheckDone && imageAnalysisLoaded && imageAnalysis && !imageAnalysisLoading && !imageAnalysisTaskId && (
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
              <div className="flex items-center gap-2">
                <span className="text-green-600">✅</span>
                <div>
                  <div className="text-sm font-medium text-green-800">이미지 속성 분석</div>
                  <div className="text-xs text-green-600">
                    {imageAnalysis.num_images?.toLocaleString()}개 이미지 분석됨
                    {imageAnalysis.cached && <span className="ml-1">(캐시됨)</span>}
                  </div>
                </div>
              </div>
              <button
                onClick={() => onLoadImageAnalysis(true)}
                className="px-3 py-1 text-xs bg-white text-green-700 border border-green-300 rounded font-medium hover:bg-green-50 transition"
              >
                🔄 재분석
              </button>
            </div>
          )}
          
          {/* 이미지 속성 분석 캐시 로딩 중 */}
          {initialCheckDone && imageAnalysisLoaded && !imageAnalysis && !imageAnalysisTaskId && (
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
              <div className="flex items-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-green-500 border-t-transparent rounded-full"></div>
                <div>
                  <div className="text-sm font-medium text-green-700">이미지 속성 분석</div>
                  <div className="text-xs text-green-600">결과 불러오는 중...</div>
                </div>
              </div>
            </div>
          )}
          
          {/* 이미지 속성 분석 미완료 */}
          {initialCheckDone && !imageAnalysisLoaded && !imageAnalysisLoading && !imageAnalysisTaskId && (
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center gap-2">
                <span className="text-blue-500">📊</span>
                <div>
                  <div className="text-sm font-medium text-blue-800">이미지 속성 분석</div>
                  <div className="text-xs text-blue-600">크기, 노이즈, 선명도, 품질 점수 분석</div>
                </div>
              </div>
              <button
                onClick={() => onLoadImageAnalysis(false)}
                className="px-3 py-1 text-xs bg-blue-600 text-white rounded font-medium hover:bg-blue-700 transition"
              >
                분석 시작
              </button>
            </div>
          )}
          
          {/* 이미지 속성 분석 진행 중 */}
          {imageAnalysisTaskId && (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-blue-500">📊</span>
                <div className="text-sm font-medium text-blue-800">이미지 속성 분석 진행 중</div>
              </div>
              <AnalysisProgress
                backend={backend}
                taskId={imageAnalysisTaskId}
                taskType="image_analysis"
                onComplete={onImageAnalysisComplete}
                variant="compact"
              />
            </div>
          )}
          
          {/* 이미지 속성 분석 준비 중 */}
          {imageAnalysisLoading && !imageAnalysisTaskId && (
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                <div>
                  <div className="text-sm font-medium text-blue-800">이미지 속성 분석</div>
                  <div className="text-xs text-blue-600">준비 중...</div>
                </div>
              </div>
            </div>
          )}
          
          {/* ----- 임베딩 분석 상태 ----- */}
          {/* 임베딩 분석 완료 */}
          {initialCheckDone && clusteringLoaded && clustering && !clusteringLoading && !clusteringTaskId && (
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
              <div className="flex items-center gap-2">
                <span className="text-green-600">✅</span>
                <div>
                  <div className="text-sm font-medium text-green-800">임베딩 분석</div>
                  <div className="text-xs text-green-600">
                    {clustering.n_clusters}개 클러스터 생성됨
                    {clustering.cached && <span className="ml-1">(캐시됨)</span>}
                  </div>
                </div>
              </div>
              <button
                onClick={() => onLoadClustering(true)}
                className="px-3 py-1 text-xs bg-white text-green-700 border border-green-300 rounded font-medium hover:bg-green-50 transition"
              >
                🔄 재분석
              </button>
            </div>
          )}
          
          {/* 임베딩 분석 캐시 로딩 중 */}
          {initialCheckDone && clusteringLoaded && !clustering && !clusteringTaskId && (
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
              <div className="flex items-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-green-500 border-t-transparent rounded-full"></div>
                <div>
                  <div className="text-sm font-medium text-green-700">임베딩 분석</div>
                  <div className="text-xs text-green-600">결과 불러오는 중...</div>
                </div>
              </div>
            </div>
          )}
          
          {/* 임베딩 분석 미완료 */}
          {initialCheckDone && !clusteringLoaded && !clusteringLoading && !clusteringTaskId && (
            <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg border border-purple-200">
              <div className="flex items-center gap-2">
                <span className="text-purple-500">🧠</span>
                <div>
                  <div className="text-sm font-medium text-purple-800">임베딩 분석</div>
                  <div className="text-xs text-purple-600">CLIP 임베딩 추출 + K-means 클러스터링</div>
                </div>
              </div>
              <button
                onClick={() => onLoadClustering(false)}
                className="px-3 py-1 text-xs bg-purple-600 text-white rounded font-medium hover:bg-purple-700 transition"
              >
                분석 시작
              </button>
            </div>
          )}
          
          {/* 임베딩 분석 진행 중 */}
          {clusteringTaskId && (
            <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-purple-500">🧠</span>
                <div className="text-sm font-medium text-purple-800">임베딩 분석 진행 중</div>
              </div>
              <AnalysisProgress
                backend={backend}
                taskId={clusteringTaskId}
                taskType="clustering"
                onComplete={onClusteringComplete}
                variant="compact"
              />
            </div>
          )}
          
          {/* 임베딩 분석 준비 중 */}
          {clusteringLoading && !clusteringTaskId && (
            <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg border border-purple-200">
              <div className="flex items-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-purple-500 border-t-transparent rounded-full"></div>
                <div>
                  <div className="text-sm font-medium text-purple-800">임베딩 분석</div>
                  <div className="text-xs text-purple-600">준비 중...</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 품질 통계 */}
      {summary?.quality_stats && summary.quality_stats.mean > 0 && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">✨ 품질 점수</div>
          <div className="grid grid-cols-4 gap-4">
            <StatCard label="평균" value={summary.quality_stats.mean?.toFixed(1)} color="blue" />
            <StatCard label="최소" value={summary.quality_stats.min?.toFixed(1)} color="red" />
            <StatCard label="최대" value={summary.quality_stats.max?.toFixed(1)} color="green" />
            <StatCard label="표준편차" value={summary.quality_stats.std?.toFixed(1)} />
          </div>
        </div>
      )}

      {/* 포맷 분포 파이 차트 */}
      {summary?.formats && Object.keys(summary.formats).length > 0 && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">📊 이미지 포맷 분포</div>
          <div className="h-64">
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={Object.entries(summary.formats).map(([name, value]) => ({ name, value }))}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                >
                  {Object.keys(summary.formats).map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Roboflow 클래스 정보 */}
      {eda.roboflow && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">🏷️ Roboflow 클래스</div>
          <div className="flex flex-wrap gap-2 mb-4">
            {eda.roboflow.classes.map((c) => (
              <span key={c} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                {c}
              </span>
            ))}
          </div>

          {/* 스플릿별 통계 */}
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(eda.roboflow.splits).map(([splitName, s]) => (
              <div key={splitName} className="p-3 bg-gray-50 rounded">
                <div className="font-semibold text-xs mb-1 capitalize">{splitName}</div>
                <div className="text-xs text-gray-600">
                  Images: {s.num_images} / Labels: {s.num_labels}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 디렉토리 구조 */}
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-2">📁 디렉토리 구조</div>
        <div className="max-h-64 overflow-auto">
          <TreeView node={eda.tree} />
        </div>
      </div>
    </div>
  );
}


/* ======================================== */
/* 분포 분석 탭 */
/* ======================================== */
function DistributionsTab({ imageAnalysis, loading, loaded, onLoad, taskId, backend, onComplete }) {
  // 아직 로드하지 않은 경우
  if (!loaded && !loading && !taskId) {
    return (
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg border border-amber-200 p-6 text-center">
        <div className="text-4xl mb-3">📈</div>
        <div className="font-semibold text-amber-800 mb-2">이미지 분포 분석</div>
        <div className="text-sm text-amber-600 mb-4">
          파일 크기, 노이즈 레벨, 선명도 분포를 분석합니다.
        </div>
        <button
          onClick={onLoad}
          className="px-6 py-2 bg-amber-500 text-white rounded-lg font-medium hover:bg-amber-600 transition shadow"
        >
          분석 시작
        </button>
      </div>
    );
  }

  // 분석 진행 중 - 프로그레스 바
  if (taskId) {
    return (
      <div className="bg-amber-50 rounded-lg border border-amber-200 p-6">
        <div className="text-center mb-4">
          <div className="text-4xl mb-3">📈</div>
          <div className="font-semibold text-amber-800 mb-2">이미지 분포 분석 중</div>
        </div>
        <AnalysisProgress
          backend={backend}
          taskId={taskId}
          taskType="image_analysis"
          onComplete={onComplete}
          variant="default"
        />
      </div>
    );
  }

  // 로딩 중 (작업 시작 전)
  if (loading && !taskId) {
    return (
      <div className="bg-amber-50 rounded-lg border border-amber-200 p-6 text-center">
        <div className="flex items-center justify-center gap-3">
          <div className="animate-spin h-6 w-6 border-2 border-amber-500 border-t-transparent rounded-full"></div>
          <div>
            <div className="font-semibold text-amber-800">분석 준비 중...</div>
            <div className="text-xs text-amber-600 mt-1">
              잠시만 기다려주세요.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const distributions = imageAnalysis?.distributions;
  const summary = imageAnalysis?.summary;

  if (!distributions) {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 text-center">
        <div className="text-gray-500">분포 데이터가 없습니다.</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 파일 크기 분포 */}
      {distributions.size && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">📏 파일 크기 분포 (MB)</div>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={distributions.size.bins.map((bin, i) => ({
                bin: bin.toFixed(3),
                count: distributions.size.counts[i]
              }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#3B82F6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {summary?.size_stats && (
            <div className="mt-2 grid grid-cols-4 gap-2 text-xs">
              <div>평균: {summary.size_stats.mean?.toFixed(4)} MB</div>
              <div>표준편차: {summary.size_stats.std?.toFixed(4)}</div>
              <div>최소: {summary.size_stats.min?.toFixed(4)} MB</div>
              <div>최대: {summary.size_stats.max?.toFixed(4)} MB</div>
            </div>
          )}
        </div>
      )}

      {/* 노이즈 분포 */}
      {distributions.noise && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">🔊 노이즈 레벨 분포</div>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={distributions.noise.bins.map((bin, i) => ({
                bin: bin.toFixed(3),
                count: distributions.noise.counts[i]
              }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#F59E0B" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 선명도 분포 */}
      {distributions.sharpness && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">🔍 선명도 분포</div>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={distributions.sharpness.bins.map((bin, i) => ({
                bin: bin.toFixed(3),
                count: distributions.sharpness.counts[i]
              }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#10B981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 품질 맵 (노이즈 vs 선명도) */}
      {distributions.quality_map && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">🎯 품질 맵 (노이즈 vs 선명도)</div>
          <div className="h-80">
            <ResponsiveContainer>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="noise"
                  name="노이즈"
                  type="number"
                  tick={{ fontSize: 10 }}
                  label={{ value: "노이즈 레벨", position: "bottom", fontSize: 11 }}
                />
                <YAxis
                  dataKey="sharpness"
                  name="선명도"
                  type="number"
                  tick={{ fontSize: 10 }}
                  label={{ value: "선명도", angle: -90, position: "left", fontSize: 11 }}
                />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                <Scatter
                  data={distributions.quality_map.noise.map((n, i) => ({
                    noise: n,
                    sharpness: distributions.quality_map.sharpness[i]
                  }))}
                  fill="#8B5CF6"
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}


/* ======================================== */
/* 임베딩 분석 탭 */
/* ======================================== */
function ClusteringTab({ clustering, loading, loaded, onLoad, taskId, backend, onComplete, initialCheckDone = true }) {
  // 초기 상태 확인 중
  if (!initialCheckDone) {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 text-center">
        <div className="flex items-center justify-center gap-3">
          <div className="animate-spin h-6 w-6 border-2 border-gray-400 border-t-transparent rounded-full"></div>
          <div>
            <div className="font-semibold text-gray-700">분석 상태 확인 중...</div>
            <div className="text-xs text-gray-500 mt-1">잠시만 기다려주세요.</div>
          </div>
        </div>
      </div>
    );
  }

  // 분석 진행 중 - 프로그레스 바 (가장 먼저 체크)
  if (taskId) {
    return (
      <div className="bg-purple-50 rounded-lg border border-purple-200 p-6">
        <div className="text-center mb-4">
          <div className="text-4xl mb-3">🧠</div>
          <div className="font-semibold text-purple-800 mb-2">임베딩 분석 중</div>
        </div>
        <AnalysisProgress
          backend={backend}
          taskId={taskId}
          taskType="clustering"
          onComplete={onComplete}
          variant="default"
        />
      </div>
    );
  }

  // 로딩 중 (작업 시작 전)
  if (loading && !taskId) {
    return (
      <div className="bg-purple-50 rounded-lg border border-purple-200 p-6 text-center">
        <div className="flex items-center justify-center gap-3">
          <div className="animate-spin h-6 w-6 border-2 border-purple-500 border-t-transparent rounded-full"></div>
          <div>
            <div className="font-semibold text-purple-800">임베딩 분석 준비 중...</div>
            <div className="text-xs text-purple-600 mt-1">
              잠시만 기다려주세요.
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 캐시된 결과 로딩 중 (캐시 있지만 데이터 아직 로드 안됨)
  if (loaded && !clustering && !taskId) {
    return (
      <div className="bg-green-50 rounded-lg border border-green-200 p-6 text-center">
        <div className="flex items-center justify-center gap-3">
          <div className="animate-spin h-6 w-6 border-2 border-green-500 border-t-transparent rounded-full"></div>
          <div>
            <div className="font-semibold text-green-700">분석 결과 불러오는 중...</div>
            <div className="text-xs text-green-600 mt-1">캐시된 결과를 로드하고 있습니다.</div>
          </div>
        </div>
      </div>
    );
  }

  // 아직 분석되지 않은 경우 - 분석 시작 버튼
  if (!clustering && !loaded) {
    return (
      <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200 p-6 text-center">
        <div className="text-4xl mb-3">🧠</div>
        <div className="font-semibold text-purple-800 mb-2">임베딩 분석</div>
        <div className="text-sm text-purple-600 mb-4">
          CLIP 임베딩을 추출하고 K-means 클러스터링을 수행합니다.<br />
          <span className="text-xs text-purple-500">(이 작업은 시간이 걸릴 수 있습니다)</span>
        </div>
        <button
          onClick={() => onLoad(false)}
          className="px-6 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition shadow"
        >
          분석 시작
        </button>
      </div>
    );
  }

  if (!clustering) {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 text-center">
        <div className="text-gray-500">임베딩 데이터가 없습니다.</div>
      </div>
    );
  }

  const { n_clusters, cluster_stats, embeddings_2d, cluster_labels, file_names } = clustering;

  // 분석 완료 상태 배너
  const CompletedBanner = () => (
    <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-200 p-4 mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-green-600 text-lg">✅</span>
          <div>
            <div className="font-semibold text-sm text-green-800">임베딩 분석 완료</div>
            <div className="text-xs text-green-600 mt-0.5">
              {clustering.num_images?.toLocaleString()}개 이미지, {n_clusters}개 클러스터
              {clustering.cached && <span className="ml-1">(캐시됨)</span>}
            </div>
          </div>
        </div>
        <button
          onClick={() => onLoad(true)}
          className="px-4 py-2 bg-white text-green-700 border border-green-300 rounded-lg text-sm font-medium hover:bg-green-50 transition flex items-center gap-2"
        >
          <span>🔄</span>
          재분석
        </button>
      </div>
    </div>
  );

  // 클러스터별 색상으로 데이터 준비
  const scatterData = embeddings_2d?.map((point, i) => ({
    x: point[0],
    y: point[1],
    cluster: cluster_labels?.[i] ?? 0,
    fileName: file_names?.[i] || `Image ${i}`
  })) || [];

  // 클러스터 크기 데이터
  const clusterSizeData = cluster_stats
    ? Object.entries(cluster_stats).map(([key, stats]) => ({
        name: key.replace('cluster_', 'Cluster '),
        size: stats.size
      }))
    : [];

  return (
    <div className="space-y-4">
      {/* 분석 완료 배너 */}
      <CompletedBanner />
      
      {/* 클러스터링 요약 */}
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-3">🧠 임베딩 분석 결과</div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <StatCard label="클러스터 수" value={n_clusters} color="blue" />
          <StatCard label="총 샘플" value={scatterData.length} />
          <StatCard label="방법" value="K-Means + CLIP" />
        </div>
      </div>

      {/* 임베딩 2D 시각화 */}
      {scatterData.length > 0 && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">📍 임베딩 공간 (PCA 2D)</div>
          <div className="h-96">
            <ResponsiveContainer>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="x" name="PC1" tick={{ fontSize: 10 }} />
                <YAxis dataKey="y" name="PC2" tick={{ fontSize: 10 }} />
                <Tooltip
                  content={({ payload }) => {
                    if (payload && payload.length > 0) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-white p-2 shadow rounded text-xs border">
                          <div className="font-medium truncate max-w-xs">{data.fileName}</div>
                          <div className="text-gray-500 mt-1">Cluster: {data.cluster}</div>
                          <div className="text-gray-400">
                            PC1: {data.x.toFixed(3)}, PC2: {data.y.toFixed(3)}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                {[...Array(n_clusters || 1)].map((_, i) => (
                  <Scatter
                    key={i}
                    name={`Cluster ${i}`}
                    data={scatterData.filter(d => d.cluster === i)}
                    fill={COLORS[i % COLORS.length]}
                  />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 클러스터 크기 분포 */}
      {clusterSizeData.length > 0 && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">📊 클러스터별 크기</div>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={clusterSizeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="size" fill="#8B5CF6">
                  {clusterSizeData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 클러스터별 파일 목록 */}
      {cluster_stats && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">📁 클러스터별 파일</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(cluster_stats).map(([key, stats]) => (
              <div key={key} className="p-3 bg-gray-50 rounded">
                <div className="font-semibold text-xs mb-2 flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[parseInt(key.replace('cluster_', '')) % COLORS.length] }}
                  ></span>
                  {key.replace('cluster_', 'Cluster ')} ({stats.size}개)
                </div>
                <div className="text-xs text-gray-600 max-h-32 overflow-auto">
                  {stats.files?.slice(0, 5).map((file, i) => (
                    <div key={i} className="truncate">{file}</div>
                  ))}
                  {stats.files?.length > 5 && (
                    <div className="text-gray-400 mt-1">+{stats.files.length - 5}개 더...</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


/* ======================================== */
/* 상세 정보 탭 */
/* ======================================== */
function DetailsTab({ eda, imageAnalysis }) {
  return (
    <div className="space-y-4">
      {/* 원시 통계 */}
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-2">📋 ZIP 통계 (원시 데이터)</div>
        <pre className="text-xs overflow-auto bg-gray-50 p-2 rounded max-h-64">
          {JSON.stringify(eda.stats, null, 2)}
        </pre>
      </div>

      {/* 이미지 분석 요약 */}
      {imageAnalysis?.summary && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-2">🖼️ 이미지 분석 요약</div>
          <pre className="text-xs overflow-auto bg-gray-50 p-2 rounded max-h-64">
            {JSON.stringify(imageAnalysis.summary, null, 2)}
          </pre>
        </div>
      )}

      {/* 해상도 분포 */}
      {imageAnalysis?.summary?.resolutions && (
        <div className="bg-white rounded shadow p-4">
          <div className="font-semibold text-sm mb-3">📐 해상도 분포 (상위 10개)</div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {Object.entries(imageAnalysis.summary.resolutions).map(([res, count]) => (
              <div key={res} className="p-2 bg-gray-50 rounded text-center">
                <div className="text-xs font-medium">{res}</div>
                <div className="text-lg font-semibold text-blue-600">{count}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 디렉토리 트리 */}
      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold text-sm mb-2">📁 전체 디렉토리 구조</div>
        <div className="max-h-96 overflow-auto">
          <TreeView node={eda.tree} />
        </div>
      </div>
    </div>
  );
}


/* ======================================== */
/* 공통 컴포넌트 */
/* ======================================== */
function StatCard({ label, value, color = "gray" }) {
  const colorClasses = {
    gray: "text-gray-800",
    blue: "text-blue-600",
    green: "text-green-600",
    red: "text-red-600",
    yellow: "text-yellow-600",
  };

  return (
    <div className="p-3 bg-gray-50 rounded">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-lg font-semibold ${colorClasses[color]}`}>{value ?? "-"}</div>
    </div>
  );
}


function TreeView({ node, depth = 0 }) {
  const [expanded, setExpanded] = useState(depth < 2);

  if (!node) return null;

  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className="ml-2">
      <div
        className={`text-xs flex items-center gap-1 py-0.5 ${hasChildren ? "cursor-pointer hover:text-blue-600" : ""}`}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren && <span className="w-3">{expanded ? "▼" : "▶"}</span>}
        {hasChildren ? "📁" : "📄"} {node.name}
      </div>
      {hasChildren && expanded && (
        <div className="ml-3 border-l border-gray-200 pl-2">
          {node.children.map((c, i) => (
            <TreeView key={`${c.name}-${i}`} node={c} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
