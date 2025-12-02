import React, { useState, useEffect, useRef } from "react";
import ZipUploader from "./ZipUploader";

export default function DatasetGrid({
  datasets,
  backend,
  refresh,
  onEDA,
  onDrift,
  onSelect,
  driftMode = false,
  compareBase = null,
  onSelectTarget,
  onBack,
  title = "데이터셋 목록",
}) {
  const [page, setPage] = useState(1);
  const [showUploader, setShowUploader] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [hoveredCard, setHoveredCard] = useState(null);
  const [clickedButton, setClickedButton] = useState({ id: null, type: null });
  const [analysisStatus, setAnalysisStatus] = useState({}); // dataset_id -> {running_tasks: [], has_running_tasks: bool}
  const pageSize = 8;
  
  // 마운트 여부 추적
  const isMountedRef = useRef(true);

  // datasets/backend가 변경될 때 상태 조회 (한 번만)
  useEffect(() => {
    isMountedRef.current = true;
    
    const fetchStatus = async () => {
      if (!datasets || datasets.length === 0) return;
      
      const statusMap = {};
      
      // 순차적으로 요청
      for (const ds of datasets) {
        if (!isMountedRef.current) break;
        try {
          const res = await fetch(`${backend}/eda/${ds.id}/status`);
          if (res.ok) {
            const data = await res.json();
            statusMap[ds.id] = data;
          }
        } catch (e) {
          // 무시
        }
      }
      
      if (isMountedRef.current) {
        setAnalysisStatus(statusMap);
      }
    };
    
    fetchStatus();
    
    // 30초 고정 간격 폴링 (단순화)
    const intervalId = setInterval(fetchStatus, 30000);
    
    return () => {
      isMountedRef.current = false;
      clearInterval(intervalId);
    };
  }, [datasets, backend]);

  // 분석 상태가 있는지 확인하는 헬퍼
  const hasRunningTasks = (datasetId) => {
    return analysisStatus[datasetId]?.has_running_tasks || false;
  };

  const getRunningTasks = (datasetId) => {
    return analysisStatus[datasetId]?.running_tasks || [];
  };

  const handleDelete = async (dataset) => {
    setIsDeleting(true);
    try {
      const res = await fetch(`${backend}/datasets/${dataset.id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        const result = await res.json();
        const deleted = result.deleted;
        alert(
          `삭제 완료!\n- EDA 결과: ${deleted.eda_results_deleted}건\n- Drift 결과: ${deleted.drift_results_deleted}건\n- 파일 삭제: ${deleted.files_deleted ? "성공" : "실패"}`
        );
        refresh();
      } else {
        const err = await res.json();
        alert(`삭제 실패: ${err.detail || "알 수 없는 오류"}`);
      }
    } catch (e) {
      alert(`삭제 중 오류 발생: ${e.message}`);
    } finally {
      setIsDeleting(false);
      setDeleteTarget(null);
    }
  };

  const handleButtonClick = (e, ds, type, handler) => {
    e.stopPropagation();
    setClickedButton({ id: ds.id, type });
    handler(ds);
  };

  const totalPages = Math.max(1, Math.ceil(datasets.length / pageSize));
  const start = (page - 1) * pageSize;
  const pageData = datasets.slice(start, start + pageSize);

  const typeLabel = (type, preview) => {
    if (type === "csv") return "CSV";
    if (type === "text") return "TEXT";
    if (type === "image") return "IMAGE";
    if (type === "video") return "VIDEO";
    if (type === "zip") {
      const zt = preview?.zip_type || "ZIP";
      return `ZIP / ${zt}`;
    }
    return "FILE";
  };

  const getTypeBadgeColor = (type) => {
    switch (type) {
      case "csv": return "bg-emerald-100 text-emerald-700 border-emerald-200";
      case "text": return "bg-blue-100 text-blue-700 border-blue-200";
      case "image": return "bg-pink-100 text-pink-700 border-pink-200";
      case "video": return "bg-purple-100 text-purple-700 border-purple-200";
      case "zip": return "bg-amber-100 text-amber-700 border-amber-200";
      default: return "bg-gray-100 text-gray-700 border-gray-200";
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          📁 {title}
          <span className="text-sm font-normal text-gray-500">
            ({datasets.length}개)
          </span>
        </h2>

        {!driftMode && (
          <button
            onClick={() => setShowUploader(!showUploader)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              showUploader
                ? "bg-gray-200 text-gray-700 hover:bg-gray-300"
                : "bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 shadow-md hover:shadow-lg"
            }`}
          >
            {showUploader ? (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                닫기
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                데이터셋 업로드
              </>
            )}
          </button>
        )}

        {driftMode && (
          <button
            className="px-4 py-2 bg-gray-500 text-white rounded-lg flex items-center gap-2 hover:bg-gray-600 transition"
            onClick={onBack}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            뒤로가기
          </button>
        )}
      </div>

      {/* 업로드 패널 */}
      {!driftMode && showUploader && (
        <div className="mb-6 p-4 bg-white border rounded-lg shadow-sm">
          <div className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            YOLOv5 데이터셋 업로드
          </div>
          <ZipUploader
            backend={backend}
            onUploadComplete={() => {
              setShowUploader(false);
              refresh();
            }}
          />
        </div>
      )}

      {/* 카드 그리드 */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        {pageData.map((ds) => {
          const hasThumb = ds.preview && ds.preview.thumbnail;
          const badge = typeLabel(ds.type, ds.preview);
          const isHovered = hoveredCard === ds.id;
          const isCompareBase = compareBase?.id === ds.id;
          const isAnalyzing = hasRunningTasks(ds.id);
          const runningTasks = getRunningTasks(ds.id);

          return (
            <div
              key={ds.id}
              className={`bg-white border-2 rounded-xl shadow-sm p-3 flex flex-col cursor-pointer transition-all duration-200 relative ${
                isCompareBase
                  ? "border-purple-400 bg-purple-50 ring-2 ring-purple-200"
                  : isAnalyzing
                    ? "border-blue-400 bg-blue-50"
                    : isHovered
                      ? "border-blue-400 shadow-md -translate-y-1"
                      : "border-gray-200 hover:border-blue-300"
              }`}
              onClick={() => !driftMode && onSelect && onSelect(ds)}
              onMouseEnter={() => setHoveredCard(ds.id)}
              onMouseLeave={() => setHoveredCard(null)}
            >
              {/* 분석 중 뱃지 */}
              {isAnalyzing && (
                <div className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 bg-blue-500 text-white rounded-full text-[10px] font-medium shadow-sm z-10">
                  <div className="animate-spin h-3 w-3 border-2 border-white border-t-transparent rounded-full"></div>
                  분석 중
                </div>
              )}
              
              {/* 타입 뱃지 */}
              <div className="mb-2">
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${getTypeBadgeColor(ds.type)}`}>
                  {badge}
                </span>
                {isCompareBase && (
                  <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-purple-500 text-white">
                    기준 데이터셋
                  </span>
                )}
              </div>

              {/* 썸네일 */}
              {hasThumb && (
                <div className="mb-2 overflow-hidden rounded-lg">
                  <img
                    src={`${backend}/files/raw?path=${encodeURIComponent(
                      ds.preview.thumbnail
                    )}`}
                    alt="thumb"
                    className="w-full h-24 object-cover transition-transform duration-300 hover:scale-105"
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
              )}

              {/* 이름 */}
              <div className="font-semibold text-sm truncate mb-1">
                {ds.name}
              </div>
              <div className="text-[11px] text-gray-500 mb-2">
                {ds.rows ?? 0} rows · {ds.cols ?? 0} cols
              </div>

              {/* 프리뷰 텍스트 */}
              <div className="flex-1 text-[11px] text-gray-600 mb-3">
                {/* CSV */}
                {ds.type === "csv" && ds.preview?.head && (
                  <pre className="whitespace-pre-wrap bg-gray-50 p-1 rounded text-[10px]">
                    {JSON.stringify(ds.preview.head[0], null, 0).slice(0, 80)}…
                  </pre>
                )}
                {/* TEXT */}
                {ds.type === "text" && ds.preview?.first_lines && (
                  <pre className="whitespace-pre-wrap bg-gray-50 p-1 rounded text-[10px]">
                    {ds.preview.first_lines.join(" ").slice(0, 80)}…
                  </pre>
                )}
                {/* ZIP */}
                {ds.type === "zip" && (
                  <div>
                    {ds.preview?.tree && (
                      <div className="text-[10px] text-gray-500 mb-1">
                        {ds.preview.tree.children?.slice(0, 3).map((c) => (
                          <div key={c.name} className="truncate">📁 {c.name}</div>
                        ))}
                        {ds.preview.tree.children?.length > 3 && (
                          <div className="text-gray-400">+{ds.preview.tree.children.length - 3}개 더...</div>
                        )}
                      </div>
                    )}
                    <div className="text-[10px] text-gray-500 flex gap-2">
                      <span>📄 {ds.preview?.stats?.total_files ?? 0}</span>
                      <span>🖼️ {ds.preview?.stats?.image_files ?? 0}</span>
                    </div>
                  </div>
                )}

                {/* 그 외 */}
                {!["csv", "text", "zip"].includes(ds.type) && (
                  <div className="text-[11px] text-gray-400">
                    {ds.preview?.info || "미리보기 없음"}
                  </div>
                )}
              </div>

              {/* 분석 진행 상태 표시 */}
              {isAnalyzing && runningTasks.length > 0 && (
                <div className="mb-2 space-y-1">
                  {runningTasks.map((task) => (
                    <div key={task.task_id} className="bg-blue-100 rounded-lg p-2">
                      <div className="flex items-center justify-between text-[10px] text-blue-700 mb-1">
                        <span className="font-medium">
                          {task.task_type === 'image_analysis' ? '📊 이미지 분석' :
                           task.task_type === 'clustering' ? '🧠 클러스터링' :
                           task.task_type === 'drift' ? '🔄 드리프트' : '⏳ 분석'}
                        </span>
                        <span>{Math.round((task.progress || 0) * 100)}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-blue-200 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${(task.progress || 0) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* 액션 버튼 */}
              <div className="flex gap-1.5 mt-auto">
                {!driftMode && (
                  <>
                    <ActionButton
                      onClick={(e) => handleButtonClick(e, ds, 'eda', onEDA)}
                      isActive={clickedButton.id === ds.id && clickedButton.type === 'eda'}
                      color="green"
                      disabled={isAnalyzing}
                      icon={
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                      }
                    >
                      EDA
                    </ActionButton>

                    <ActionButton
                      onClick={(e) => handleButtonClick(e, ds, 'drift', onDrift)}
                      isActive={clickedButton.id === ds.id && clickedButton.type === 'drift'}
                      color="purple"
                      disabled={isAnalyzing}
                      icon={
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                        </svg>
                      }
                    >
                      Drift
                    </ActionButton>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(ds);
                      }}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                      title="삭제"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </>
                )}

                {driftMode && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectTarget(ds);
                    }}
                    disabled={ds.id === compareBase?.id}
                    className={`flex-1 px-3 py-2 text-xs rounded-lg font-medium transition-all flex items-center justify-center gap-1.5 ${
                      ds.id === compareBase?.id
                        ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                        : "bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 shadow hover:shadow-md"
                    }`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    비교하기
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 빈 상태 */}
      {datasets.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <div className="text-4xl mb-3">📂</div>
          <div className="font-medium">아직 데이터셋이 없습니다.</div>
          <div className="text-sm mt-1">위의 업로드 버튼을 클릭하여 데이터셋을 추가하세요.</div>
        </div>
      )}

      {/* 페이지네이션 */}
      {datasets.length > 0 && (
        <div className="flex justify-center items-center gap-2 text-xs">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 border rounded-lg disabled:opacity-50 hover:bg-gray-50 transition flex items-center gap-1"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            이전
          </button>
          <span className="px-3 py-1.5 bg-gray-100 rounded-lg font-medium">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 border rounded-lg disabled:opacity-50 hover:bg-gray-50 transition flex items-center gap-1"
          >
            다음
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      )}

      {/* 삭제 확인 모달 */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  데이터셋 삭제
                </h3>
                <p className="text-sm text-gray-500">
                  이 작업은 되돌릴 수 없습니다.
                </p>
              </div>
            </div>
            
            <p className="text-sm text-gray-600 mb-4">
              <strong className="text-gray-900">{deleteTarget.name}</strong>을(를) 삭제하시겠습니까?
            </p>
            
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
              <p className="text-xs text-amber-800 font-medium mb-1">
                ⚠️ 다음 항목이 함께 삭제됩니다:
              </p>
              <ul className="text-xs text-amber-700 list-disc list-inside space-y-0.5">
                <li>관련된 EDA 분석 결과</li>
                <li>관련된 Drift 분석 결과</li>
                <li>업로드된 데이터 파일</li>
              </ul>
            </div>
            
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition"
              >
                취소
              </button>
              <button
                onClick={() => handleDelete(deleteTarget)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm text-white bg-red-500 rounded-lg hover:bg-red-600 disabled:opacity-50 transition flex items-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                    삭제 중...
                  </>
                ) : (
                  "삭제"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


/* ======================================== */
/* 액션 버튼 컴포넌트 */
/* ======================================== */
function ActionButton({ onClick, isActive, color, icon, children, disabled = false }) {
  const colorClasses = {
    green: {
      base: "bg-emerald-500 hover:bg-emerald-600",
      active: "bg-emerald-600 ring-2 ring-emerald-300 ring-offset-1",
      disabled: "bg-gray-300 cursor-not-allowed",
    },
    purple: {
      base: "bg-purple-500 hover:bg-purple-600",
      active: "bg-purple-600 ring-2 ring-purple-300 ring-offset-1",
      disabled: "bg-gray-300 cursor-not-allowed",
    },
  };

  const classes = colorClasses[color];

  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      className={`flex-1 px-2 py-1.5 text-[11px] text-white rounded-lg font-medium transition-all flex items-center justify-center gap-1 ${
        disabled ? classes.disabled : isActive ? classes.active : classes.base
      }`}
    >
      {icon}
      {children}
    </button>
  );
}
