import React, { useEffect, useState } from 'react';
import { useTaskWebSocket, useTaskPolling } from '../hooks/useTaskWebSocket';

/**
 * 분석 작업 진행률 표시 컴포넌트
 * 
 * @param {Object} props
 * @param {string} props.backend - 백엔드 URL
 * @param {string} props.taskId - 작업 ID
 * @param {string} props.taskType - 작업 유형 (image_analysis, clustering, drift)
 * @param {function} props.onComplete - 완료 콜백
 * @param {function} props.onError - 에러 콜백
 * @param {boolean} props.usePolling - WebSocket 대신 폴링 사용 (기본 false)
 * @param {string} props.variant - 스타일 변형 (default, compact, inline)
 */
export default function AnalysisProgress({
  backend,
  taskId,
  taskType = 'analysis',
  onComplete,
  onError,
  usePolling = false,
  variant = 'default',
}) {
  const [displayStatus, setDisplayStatus] = useState(null);

  // WebSocket 또는 폴링으로 상태 수신
  const wsResult = useTaskWebSocket(
    backend,
    !usePolling ? taskId : null,
    {
      onProgress: setDisplayStatus,
      onComplete: (data) => {
        setDisplayStatus(data);
        if (onComplete) onComplete(data);
      },
      onError,
    }
  );

  const pollingResult = useTaskPolling(
    backend,
    usePolling ? taskId : null,
    {
      interval: 1000,
      onComplete: (data) => {
        setDisplayStatus(data);
        if (onComplete) onComplete(data);
      },
    }
  );

  const status = usePolling ? pollingResult.status : displayStatus;

  if (!status) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
        연결 중...
      </div>
    );
  }

  const progress = status.progress || 0;
  const percentage = Math.round(progress * 100);
  const message = status.message || '처리 중...';
  const metadata = status.metadata || {};
  const isComplete = status.status === 'completed';
  const isFailed = status.status === 'failed';

  // 작업 유형별 색상
  const getProgressColor = () => {
    if (isFailed) return 'bg-red-500';
    if (isComplete) return 'bg-green-500';
    
    switch (taskType) {
      case 'image_analysis':
        return 'bg-amber-500';
      case 'clustering':
        return 'bg-purple-500';
      case 'drift':
        return 'bg-blue-500';
      default:
        return 'bg-blue-500';
    }
  };

  // 작업 유형별 아이콘
  const getTaskIcon = () => {
    if (isFailed) return '❌';
    if (isComplete) return '✅';
    
    switch (taskType) {
      case 'image_analysis':
        return '📊';
      case 'clustering':
        return '🧠';
      case 'drift':
        return '🔄';
      default:
        return '⏳';
    }
  };

  // Compact 변형
  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${getProgressColor()} transition-all duration-300 ease-out`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <span className="text-xs text-gray-500 w-12 text-right">{percentage}%</span>
      </div>
    );
  }

  // Inline 변형
  if (variant === 'inline') {
    return (
      <div className="flex items-center gap-2 text-sm">
        {!isComplete && !isFailed && (
          <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
        )}
        <span className={isFailed ? 'text-red-500' : isComplete ? 'text-green-500' : 'text-gray-600'}>
          {getTaskIcon()} {message}
        </span>
        {!isComplete && !isFailed && (
          <span className="text-gray-400">({percentage}%)</span>
        )}
      </div>
    );
  }

  // Default 변형
  return (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{getTaskIcon()}</span>
          <span className={`text-sm font-medium ${
            isFailed ? 'text-red-700' : isComplete ? 'text-green-700' : 'text-gray-700'
          }`}>
            {message}
          </span>
        </div>
        <span className={`text-sm font-bold ${
          isFailed ? 'text-red-500' : isComplete ? 'text-green-500' : 'text-blue-500'
        }`}>
          {percentage}%
        </span>
      </div>

      {/* 프로그레스 바 */}
      <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-3">
        <div
          className={`h-full ${getProgressColor()} transition-all duration-500 ease-out rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* 상세 정보 */}
      <div className="flex justify-between text-xs text-gray-500">
        <div className="flex items-center gap-4">
          {/* 처리 파일 수 */}
          {metadata.processed !== undefined && metadata.total_files !== undefined && (
            <span>
              📁 {metadata.processed} / {metadata.total_files} 파일
            </span>
          )}
          
          {/* 경과 시간 */}
          {metadata.elapsed_seconds !== undefined && (
            <span>
              ⏱️ {formatTime(metadata.elapsed_seconds)}
            </span>
          )}
        </div>

        {/* 예상 남은 시간 */}
        {!isComplete && !isFailed && metadata.eta_formatted && (
          <span className="text-gray-400">
            남은 시간: {metadata.eta_formatted}
          </span>
        )}

        {/* 에러 메시지 */}
        {isFailed && status.error && (
          <span className="text-red-500 truncate max-w-xs" title={status.error}>
            오류: {status.error}
          </span>
        )}
      </div>
    </div>
  );
}


/**
 * 여러 작업의 진행률을 표시하는 컴포넌트
 */
export function MultiTaskProgress({ backend, tasks, onTaskComplete }) {
  if (!tasks || tasks.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {tasks.map((task) => (
        <AnalysisProgress
          key={task.task_id}
          backend={backend}
          taskId={task.task_id}
          taskType={task.task_type}
          onComplete={(data) => onTaskComplete?.(task.task_id, data)}
          variant="default"
        />
      ))}
    </div>
  );
}


/**
 * 분석 시작 버튼 + 진행률 통합 컴포넌트
 */
export function AnalysisButton({
  backend,
  datasetId,
  analysisType,
  label,
  icon,
  onComplete,
  className = '',
  disabled = false,
}) {
  const [taskId, setTaskId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleStart = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const endpoint = analysisType === 'drift'
        ? `${backend}/drift/async`
        : `${backend}/eda/async/${datasetId}/${analysisType}`;
      
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: analysisType === 'drift' ? JSON.stringify({
          base_id: datasetId,
          target_id: datasetId,  // 실제 사용 시 타겟 ID 필요
        }) : undefined,
      });

      const data = await res.json();

      if (data.status === 'queued') {
        setTaskId(data.task_id);
      } else if (data.status === 'already_running') {
        setTaskId(data.task_id);
      } else if (data.status === 'completed' && data.cached) {
        // 이미 캐시된 결과 있음
        if (onComplete) onComplete(data);
      } else {
        setError(data.message || '알 수 없는 응답');
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleComplete = (data) => {
    setTaskId(null);
    if (onComplete) onComplete(data);
  };

  // 진행 중
  if (taskId) {
    return (
      <div className="space-y-2">
        <AnalysisProgress
          backend={backend}
          taskId={taskId}
          taskType={analysisType}
          onComplete={handleComplete}
          onError={setError}
        />
      </div>
    );
  }

  // 버튼
  return (
    <div className="space-y-2">
      <button
        onClick={handleStart}
        disabled={disabled || isLoading}
        className={`flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
          disabled || isLoading
            ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
            : 'bg-blue-500 text-white hover:bg-blue-600 shadow hover:shadow-md'
        } ${className}`}
      >
        {isLoading ? (
          <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
        ) : (
          <span>{icon}</span>
        )}
        {label}
      </button>

      {error && (
        <div className="text-xs text-red-500">{error}</div>
      )}
    </div>
  );
}


// 헬퍼 함수
function formatTime(seconds) {
  if (seconds === null || seconds === undefined) return '-';
  
  const s = Math.round(seconds);
  if (s < 60) return `${s}초`;
  
  const m = Math.floor(s / 60);
  const remainS = s % 60;
  
  if (m < 60) {
    return remainS > 0 ? `${m}분 ${remainS}초` : `${m}분`;
  }
  
  const h = Math.floor(m / 60);
  const remainM = m % 60;
  return remainM > 0 ? `${h}시간 ${remainM}분` : `${h}시간`;
}
