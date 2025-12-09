import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";

/**
 * SnapshotTimeline - View and manage snapshots with lineage visualization
 */
export default function SnapshotTimeline({ 
  workspaceId, 
  workspaceApi,
  currentSnapshot: externalCurrentSnapshot,
  onSnapshotChange
}) {
  const [snapshots, setSnapshots] = useState([]);
  const [currentSnapshot, setCurrentSnapshot] = useState(null);
  const [lineage, setLineage] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [restoring, setRestoring] = useState(null);

  // Create snapshot form
  const [message, setMessage] = useState("");
  const [alias, setAlias] = useState("");

  // Load snapshots and lineage
  const loadSnapshots = useCallback(async () => {
    try {
      setLoading(true);
      
      const [snapshotsRes, currentRes, lineageRes] = await Promise.all([
        axios.get(`${workspaceApi}/workspace/${workspaceId}/snapshots`),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/snapshot/current`).catch(() => ({ data: null })),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/lineage`).catch(() => ({ data: { nodes: [], edges: [] } })),
      ]);
      
      setSnapshots(snapshotsRes.data || []);
      setCurrentSnapshot(currentRes.data);
      setLineage(lineageRes.data || { nodes: [], edges: [] });
    } catch (err) {
      console.error("Failed to load snapshots:", err);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, workspaceApi]);

  useEffect(() => {
    loadSnapshots();
  }, [loadSnapshots]);

  // Sync with external current snapshot
  useEffect(() => {
    if (externalCurrentSnapshot !== undefined) {
      setCurrentSnapshot(
        snapshots.find(s => s.snapshot_id === externalCurrentSnapshot) || null
      );
    }
  }, [externalCurrentSnapshot, snapshots]);

  // Create snapshot
  const createSnapshot = async () => {
    if (!message.trim()) {
      alert("스냅샷 메시지를 입력해주세요");
      return;
    }

    try {
      setCreating(true);
      
      await axios.post(`${workspaceApi}/workspace/${workspaceId}/snapshot`, {
        message,
        alias: alias.trim() || null,
      });

      setMessage("");
      setAlias("");
      await loadSnapshots();
      
      // Notify parent of snapshot change
      if (onSnapshotChange) {
        onSnapshotChange();
      }
    } catch (err) {
      console.error("Failed to create snapshot:", err);
      alert(err.response?.data?.detail || "스냅샷 생성 실패");
    } finally {
      setCreating(false);
    }
  };

  // Restore snapshot (checkout)
  const restoreSnapshot = async (snapshotId) => {
    if (!confirm(`스냅샷 ${snapshotId}로 체크아웃하시겠습니까?`)) {
      return;
    }

    try {
      setRestoring(snapshotId);
      
      await axios.post(
        `${workspaceApi}/workspace/${workspaceId}/snapshot/${snapshotId}/restore`,
        { force: false }
      );

      await loadSnapshots();
      
      // Notify parent of snapshot change
      if (onSnapshotChange) {
        onSnapshotChange();
      }
    } catch (err) {
      console.error("Failed to restore snapshot:", err);
      alert(err.response?.data?.detail || "스냅샷 체크아웃 실패");
    } finally {
      setRestoring(null);
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
      {/* Create snapshot */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-semibold mb-4">📸 새 스냅샷 생성</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">메시지 *</label>
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="예: 노이즈 제거 후 상태"
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">별칭 (선택)</label>
            <input
              type="text"
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder="예: clean_v1"
              className="w-full px-3 py-2 border rounded"
            />
          </div>
        </div>
        <button
          onClick={createSnapshot}
          disabled={creating}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {creating ? "생성 중..." : "스냅샷 생성"}
        </button>
      </div>

      {/* Current snapshot indicator */}
      {currentSnapshot && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded flex items-center gap-2">
          <span className="text-green-600">✓</span>
          <span className="text-sm">
            현재 스냅샷: <strong>{currentSnapshot.snapshot_id}</strong>
            {currentSnapshot.alias && ` (${currentSnapshot.alias})`}
          </span>
        </div>
      )}

      {/* Lineage Graph */}
      {lineage.nodes.length > 0 && (
        <div className="mb-6">
          <h3 className="font-semibold mb-4">🔗 스냅샷 계보</h3>
          <div className="p-4 bg-white border rounded-lg overflow-x-auto">
            <div className="flex items-center gap-2 min-w-max">
              {lineage.nodes.map((node, index) => {
                const isCurrent = currentSnapshot?.snapshot_id === node.id;
                const hasParent = lineage.edges.some(e => e.to_id === node.id);
                
                return (
                  <React.Fragment key={node.id}>
                    {/* Arrow from parent */}
                    {hasParent && index > 0 && (
                      <div className="flex items-center">
                        <div className="w-8 h-0.5 bg-gray-300"></div>
                        <div className="w-0 h-0 border-t-4 border-b-4 border-l-4 border-transparent border-l-gray-300"></div>
                      </div>
                    )}
                    
                    {/* Node */}
                    <div
                      className={`relative p-3 rounded-lg border-2 cursor-pointer transition-all min-w-32 ${
                        isCurrent
                          ? "border-green-500 bg-green-50 shadow-md"
                          : "border-gray-200 bg-white hover:border-gray-300"
                      }`}
                      onClick={() => !isCurrent && restoreSnapshot(node.id)}
                      title={node.description}
                    >
                      {isCurrent && (
                        <div className="absolute -top-2 -right-2 w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                          <span className="text-white text-xs">✓</span>
                        </div>
                      )}
                      <div className="font-medium text-sm">{node.id}</div>
                      {node.alias && (
                        <div className="text-xs text-blue-600">{node.alias}</div>
                      )}
                      <div className="text-xs text-gray-400 mt-1 truncate max-w-28">
                        {node.description}
                      </div>
                    </div>
                  </React.Fragment>
                );
              })}
            </div>
            <div className="mt-2 text-xs text-gray-400">
              클릭하여 해당 스냅샷으로 체크아웃
            </div>
          </div>
        </div>
      )}

      {/* Snapshot timeline */}
      <h3 className="font-semibold mb-4">📜 스냅샷 히스토리 (시간순)</h3>
      
      {snapshots.length > 0 ? (
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200"></div>
          
          {/* Snapshots */}
          <div className="space-y-4">
            {snapshots.map((snapshot, index) => {
              const isCurrent = currentSnapshot?.snapshot_id === snapshot.snapshot_id;
              
              return (
                <div key={snapshot.snapshot_id} className="relative pl-14">
                  {/* Timeline dot */}
                  <div
                    className={`absolute left-4 w-5 h-5 rounded-full border-2 ${
                      isCurrent
                        ? "bg-green-500 border-green-500"
                        : "bg-white border-gray-300"
                    }`}
                  ></div>
                  
                  {/* Snapshot card */}
                  <div
                    className={`p-4 border rounded-lg ${
                      isCurrent ? "border-green-300 bg-green-50" : "bg-white"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{snapshot.snapshot_id}</span>
                          {snapshot.alias && (
                            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                              {snapshot.alias}
                            </span>
                          )}
                          {isCurrent && (
                            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">
                              현재
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          {snapshot.description}
                        </div>
                        <div className="text-xs text-gray-400 mt-2">
                          <span>Git: {snapshot.git_commit}</span>
                          <span className="mx-2">|</span>
                          <span>Data: {snapshot.data_hash}</span>
                          <span className="mx-2">|</span>
                          <span>{new Date(snapshot.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {!isCurrent && (
                          <button
                            onClick={() => restoreSnapshot(snapshot.snapshot_id)}
                            disabled={restoring === snapshot.snapshot_id}
                            className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
                          >
                            {restoring === snapshot.snapshot_id ? "체크아웃 중..." : "체크아웃"}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="p-8 bg-gray-50 rounded text-center text-gray-500">
          <div className="text-4xl mb-2">📷</div>
          <div>스냅샷이 없습니다</div>
          <div className="text-sm text-gray-400 mt-1">
            위의 폼을 사용하여 첫 스냅샷을 생성하세요
          </div>
        </div>
      )}

      {/* Snapshot description */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg text-sm text-blue-800">
        <strong>💡 스냅샷과 체크아웃</strong>
        <p className="mt-1">
          <strong>스냅샷</strong>은 워크스페이스의 상태(데이터 + 코드)를 Git/DVC로 버전 관리합니다.
          데이터를 변형(필터링, 삭제 등)하면 새 스냅샷이 필수로 생성됩니다.
        </p>
        <p className="mt-1">
          <strong>체크아웃</strong>으로 이전 스냅샷 상태로 돌아갈 수 있습니다.
          체크아웃된 상태에서 분석, 실험 등 모든 작업이 수행됩니다.
        </p>
      </div>
    </div>
  );
}
