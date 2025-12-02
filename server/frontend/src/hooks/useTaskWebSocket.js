import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * 작업 진행률을 WebSocket으로 실시간 수신하는 훅
 * 
 * @param {string} backend - 백엔드 URL (http://...)
 * @param {string|null} taskId - 작업 ID (null이면 연결 안 함)
 * @param {Object} options - 옵션
 * @param {function} options.onProgress - 진행률 업데이트 콜백
 * @param {function} options.onComplete - 완료 콜백
 * @param {function} options.onError - 에러 콜백
 * @param {boolean} options.autoReconnect - 자동 재연결 여부 (기본 true)
 */
export function useTaskWebSocket(backend, taskId, options = {}) {
  const {
    onProgress,
    onComplete,
    onError,
    autoReconnect = true,
  } = options;

  const [status, setStatus] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  
  // 콜백들을 ref로 저장하여 의존성 문제 해결
  const onProgressRef = useRef(onProgress);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  
  // 콜백 refs 업데이트
  useEffect(() => {
    onProgressRef.current = onProgress;
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onProgress, onComplete, onError]);

  // taskId와 backend 변경 시에만 연결/해제
  useEffect(() => {
    // taskId가 없으면 연결 안 함
    if (!backend || !taskId) {
      return;
    }

    // 이전 연결 및 타이머 정리
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    // WebSocket URL 생성
    const wsProtocol = backend.startsWith('https') ? 'wss' : 'ws';
    const wsBase = backend.replace(/^https?/, wsProtocol);
    const wsUrl = `${wsBase}/ws/task/${taskId}`;

    // 연결 함수 (재연결용)
    const createConnection = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('📡 WebSocket 연결됨:', taskId);
          setIsConnected(true);
          setError(null);
          reconnectAttemptsRef.current = 0;
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setStatus(data);

            // 진행률 콜백 호출 (ref 사용)
            if (onProgressRef.current) {
              onProgressRef.current(data);
            }

            // 완료 또는 실패 시 콜백 호출
            if (data.status === 'completed' || data.status === 'failed') {
              if (onCompleteRef.current) {
                onCompleteRef.current(data);
              }
              // 완료 후 연결 종료
              ws.close();
            }

            // 에러 응답
            if (data.error && onErrorRef.current) {
              onErrorRef.current(data.error);
            }
          } catch (e) {
            console.error('WebSocket 메시지 파싱 실패:', e);
          }
        };

        ws.onclose = (event) => {
          console.log('📡 WebSocket 연결 종료:', taskId, event.code);
          setIsConnected(false);
          wsRef.current = null;

          // 비정상 종료 시 재연결 시도
          if (
            autoReconnect && 
            !event.wasClean && 
            reconnectAttemptsRef.current < maxReconnectAttempts
          ) {
            reconnectAttemptsRef.current += 1;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
            console.log(`🔄 재연결 시도 ${reconnectAttemptsRef.current}/${maxReconnectAttempts} (${delay}ms 후)`);
            
            reconnectTimeoutRef.current = setTimeout(() => {
              createConnection();
            }, delay);
          }
        };

        ws.onerror = (event) => {
          console.error('⚠️ WebSocket 오류:', event);
          setError('WebSocket 연결 오류');
          if (onErrorRef.current) {
            onErrorRef.current('WebSocket 연결 오류');
          }
        };
      } catch (e) {
        console.error('WebSocket 생성 실패:', e);
        setError(e.message);
      }
    };

    // 연결 시작
    createConnection();

    // 클린업
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setIsConnected(false);
    };
  }, [backend, taskId, autoReconnect]); // 콜백 의존성 제거!

  // 수동 연결 해제
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  return {
    status,
    isConnected,
    error,
    disconnect,
  };
}


/**
 * 특정 데이터셋의 분석 상태를 실시간으로 수신하는 훅
 * 
 * @param {string} backend - 백엔드 URL
 * @param {string|null} datasetId - 데이터셋 ID
 */
export function useDatasetTasksWebSocket(backend, datasetId) {
  const [tasks, setTasks] = useState([]);
  const [hasRunningTasks, setHasRunningTasks] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  
  const wsRef = useRef(null);

  useEffect(() => {
    if (!backend || !datasetId) return;

    const wsProtocol = backend.startsWith('https') ? 'wss' : 'ws';
    const wsBase = backend.replace(/^https?/, wsProtocol);
    const wsUrl = `${wsBase}/ws/dataset/${datasetId}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setTasks(data.running_tasks || []);
          setHasRunningTasks(data.has_running_tasks || false);
        } catch (e) {
          console.error('WebSocket 메시지 파싱 실패:', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
      };

      ws.onerror = (event) => {
        console.error('WebSocket 오류:', event);
      };
    } catch (e) {
      console.error('WebSocket 생성 실패:', e);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [backend, datasetId]);

  return {
    tasks,
    hasRunningTasks,
    isConnected,
  };
}


/**
 * 폴링 기반 작업 상태 조회 훅 (WebSocket 대안)
 * 
 * @param {string} backend - 백엔드 URL
 * @param {string|null} taskId - 작업 ID
 * @param {Object} options - 옵션
 * @param {number} options.interval - 폴링 간격 (ms, 기본 2000)
 * @param {function} options.onComplete - 완료 콜백
 */
export function useTaskPolling(backend, taskId, options = {}) {
  const {
    interval = 2000,
    onComplete,
  } = options;

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const intervalRef = useRef(null);
  const onCompleteRef = useRef(onComplete);
  
  // 콜백 ref 업데이트
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    if (!backend || !taskId) {
      setStatus(null);
      return;
    }

    const fetchStatus = async () => {
      try {
        setLoading(true);
        const res = await fetch(`${backend}/eda/task/${taskId}`);
        
        if (!res.ok) {
          throw new Error('작업 상태 조회 실패');
        }
        
        const data = await res.json();
        setStatus(data);
        setError(null);

        // 완료 또는 실패 시 폴링 중지
        if (data.status === 'completed' || data.status === 'failed') {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          if (onCompleteRef.current) {
            onCompleteRef.current(data);
          }
        }
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    // 즉시 한 번 호출
    fetchStatus();

    // 주기적 폴링
    intervalRef.current = setInterval(fetchStatus, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [backend, taskId, interval]); // onComplete 의존성 제거!

  return {
    status,
    loading,
    error,
  };
}


export default useTaskWebSocket;
