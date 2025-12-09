import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useSearchParams } from "react-router-dom";

// Workspace sub-components
import DataExplorer from "./workspace/DataExplorer";
import DataSampler from "./workspace/DataSampler";
import AnalysisPanel from "./workspace/AnalysisPanel";
import ExperimentPanel from "./workspace/ExperimentPanel";
import SnapshotTimeline from "./workspace/SnapshotTimeline";

// Configuration
// 리버스 프록시 환경: API 경로에 이미 /workspace/ 포함되어 있음
const WORKSPACE_API = "";

/**
 * WorkspaceStudio - Main component for ddoc workspace management
 * 
 * Provides UI for:
 * - Global snapshot state management (checkout)
 * - Data exploration and preview
 * - Data transformation (sampling/filtering)
 * - Analysis (embedding, attributes)
 * - Training experiments
 * - Snapshot history and lineage
 */
export default function WorkspaceStudio({
  datasets,
  onBack,
}) {
  const [searchParams] = useSearchParams();
  
  // Get base/target IDs from URL params
  const baseId = searchParams.get("base");
  const targetId = searchParams.get("target");
  
  // Find datasets from IDs
  const baseDataset = datasets.find((d) => d.id === baseId);
  const targetDataset = datasets.find((d) => d.id === targetId);
  
  // State
  const [activeWorkspace, setActiveWorkspace] = useState("base"); // 'base' | 'target'
  const [activeTab, setActiveTab] = useState("explore");
  const [workspaces, setWorkspaces] = useState({ base: null, target: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  
  // Global snapshot state
  const [currentSnapshot, setCurrentSnapshot] = useState(null);
  const [hasUncommittedChanges, setHasUncommittedChanges] = useState(false);
  const [snapshots, setSnapshots] = useState([]);
  const [checkingOut, setCheckingOut] = useState(false);

  // Get current workspace ID
  const currentWorkspaceId = activeWorkspace === "base"
    ? workspaces.base?.workspace_id
    : workspaces.target?.workspace_id;

  // Initialize or load workspaces
  const loadWorkspaces = useCallback(async () => {
    try {
      setLoading(true);
      
      // Try to load existing workspaces
      const response = await axios.get(`${WORKSPACE_API}/workspaces`);
      const existingWorkspaces = response.data;

      // Find base and target workspaces for this drift analysis
      const baseWs = existingWorkspaces.find(
        (ws) => ws.source_dataset_id === baseDataset?.id && ws.dataset_type === "base"
      );
      const targetWs = existingWorkspaces.find(
        (ws) => ws.source_dataset_id === targetDataset?.id && ws.dataset_type === "target"
      );

      setWorkspaces({
        base: baseWs || null,
        target: targetWs || null,
      });
    } catch (err) {
      console.error("Failed to load workspaces:", err);
      // Don't set error - workspaces just don't exist yet
    } finally {
      setLoading(false);
    }
  }, [baseDataset, targetDataset]);

  // Load global snapshot state for current workspace
  const loadSnapshotState = useCallback(async () => {
    if (!currentWorkspaceId) return;
    
    try {
      // Load workspace status (current snapshot, uncommitted changes)
      const statusRes = await axios.get(
        `${WORKSPACE_API}/workspace/${currentWorkspaceId}/status`
      );
      setCurrentSnapshot(statusRes.data.current_snapshot);
      setHasUncommittedChanges(statusRes.data.uncommitted_changes || false);
      
      // Load snapshot list
      const snapshotsRes = await axios.get(
        `${WORKSPACE_API}/workspace/${currentWorkspaceId}/snapshots`
      );
      setSnapshots(snapshotsRes.data || []);
    } catch (err) {
      console.error("Failed to load snapshot state:", err);
    }
  }, [currentWorkspaceId]);

  // Checkout a specific snapshot
  const checkoutSnapshot = async (snapshotId) => {
    if (!currentWorkspaceId || !snapshotId) return;
    
    try {
      setCheckingOut(true);
      setError(null);
      
      await axios.post(
        `${WORKSPACE_API}/workspace/${currentWorkspaceId}/snapshot/${snapshotId}/restore`,
        { force: false }
      );
      
      // Reload snapshot state
      await loadSnapshotState();
    } catch (err) {
      console.error("Failed to checkout snapshot:", err);
      setError(`스냅샷 체크아웃 실패: ${err.response?.data?.detail || err.message}`);
    } finally {
      setCheckingOut(false);
    }
  };

  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces]);

  // Load snapshot state when workspace changes
  useEffect(() => {
    if (currentWorkspaceId) {
      loadSnapshotState();
    }
  }, [currentWorkspaceId, loadSnapshotState]);

  // Create workspace
  const createWorkspace = async (type) => {
    const dataset = type === "base" ? baseDataset : targetDataset;
    if (!dataset) return;

    try {
      setCreating(true);
      setError(null);

      const response = await axios.post(`${WORKSPACE_API}/workspace/create`, {
        dataset_id: dataset.id,
        dataset_type: type,
        source_path: dataset.path || `/data/${dataset.id}`,
        name: `${dataset.name}_workspace`,
      });

      setWorkspaces((prev) => ({
        ...prev,
        [type]: response.data,
      }));
    } catch (err) {
      console.error("Failed to create workspace:", err);
      setError(`워크스페이스 생성 실패: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  // Tab configuration
  const tabs = [
    { id: "explore", label: "🔍 데이터 탐색", icon: "🔍" },
    { id: "transform", label: "✂️ 데이터 변형", icon: "✂️" },
    { id: "analysis", label: "📊 분석", icon: "📊" },
    { id: "experiment", label: "🧪 실험", icon: "🧪" },
    { id: "snapshots", label: "📸 스냅샷", icon: "📸" },
  ];

  // Loading state
  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-4">
        <div className="flex items-center justify-center gap-3 py-12">
          <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
          <span className="text-gray-600">워크스페이스 로딩 중...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        {onBack && (
          <button
            onClick={onBack}
            className="px-3 py-2 bg-gray-200 rounded text-sm hover:bg-gray-300 transition"
          >
            ← 드리프트 분석으로 돌아가기
          </button>
        )}
        <h1 className="text-xl font-semibold">ddoc 워크스페이스</h1>
      </div>

      {/* Error display */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Workspace selector */}
      <div className="flex gap-4 mb-6">
        {/* Base workspace card */}
        <div
          className={`flex-1 p-4 border-2 rounded-lg cursor-pointer transition ${
            activeWorkspace === "base"
              ? "border-blue-500 bg-blue-50"
              : "border-gray-200 hover:border-gray-300"
          }`}
          onClick={() => workspaces.base && setActiveWorkspace("base")}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Base (Source)</span>
            {workspaces.base && (
              <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">
                활성
              </span>
            )}
          </div>
          <div className="font-semibold">{baseDataset?.name || "Base Dataset"}</div>
          {workspaces.base ? (
            <div className="mt-2 text-xs text-gray-500">
              스냅샷: {workspaces.base.snapshot_count} | 실험: {workspaces.base.experiment_count}
            </div>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                createWorkspace("base");
              }}
              disabled={creating}
              className="mt-2 px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50"
            >
              {creating ? "생성 중..." : "워크스페이스 생성"}
            </button>
          )}
        </div>

        {/* Target workspace card */}
        <div
          className={`flex-1 p-4 border-2 rounded-lg cursor-pointer transition ${
            activeWorkspace === "target"
              ? "border-purple-500 bg-purple-50"
              : "border-gray-200 hover:border-gray-300"
          }`}
          onClick={() => workspaces.target && setActiveWorkspace("target")}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Target</span>
            {workspaces.target && (
              <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">
                활성
              </span>
            )}
          </div>
          <div className="font-semibold">{targetDataset?.name || "Target Dataset"}</div>
          {workspaces.target ? (
            <div className="mt-2 text-xs text-gray-500">
              스냅샷: {workspaces.target.snapshot_count} | 실험: {workspaces.target.experiment_count}
            </div>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                createWorkspace("target");
              }}
              disabled={creating}
              className="mt-2 px-3 py-1 bg-purple-500 text-white text-sm rounded hover:bg-purple-600 disabled:opacity-50"
            >
              {creating ? "생성 중..." : "워크스페이스 생성"}
            </button>
          )}
        </div>
      </div>

      {/* Main content area */}
      {currentWorkspaceId ? (
        <>
          {/* Global Snapshot State */}
          <div className="mb-4 p-4 bg-gray-50 border rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div>
                  <div className="text-xs text-gray-500 mb-1">현재 스냅샷 상태</div>
                  <div className="flex items-center gap-2">
                    <select
                      value={currentSnapshot || ""}
                      onChange={(e) => {
                        if (e.target.value && e.target.value !== currentSnapshot) {
                          checkoutSnapshot(e.target.value);
                        }
                      }}
                      disabled={checkingOut}
                      className="px-3 py-2 border rounded font-medium bg-white"
                    >
                      {snapshots.length === 0 ? (
                        <option value="">스냅샷 없음</option>
                      ) : (
                        snapshots.map((snap) => (
                          <option key={snap.snapshot_id} value={snap.snapshot_id}>
                            {snap.snapshot_id}
                            {snap.alias ? ` (${snap.alias})` : ""}
                            {snap.snapshot_id === currentSnapshot ? " ← 현재" : ""}
                          </option>
                        ))
                      )}
                    </select>
                    {checkingOut && (
                      <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                    )}
                  </div>
                </div>
                <div className="border-l pl-4">
                  <div className="text-xs text-gray-500 mb-1">상태</div>
                  {hasUncommittedChanges ? (
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-sm rounded">
                      ⚠️ 변경사항 있음
                    </span>
                  ) : currentSnapshot ? (
                    <span className="px-2 py-1 bg-green-100 text-green-700 text-sm rounded">
                      ✓ 체크아웃됨
                    </span>
                  ) : (
                    <span className="px-2 py-1 bg-gray-100 text-gray-600 text-sm rounded">
                      초기 상태
                    </span>
                  )}
                </div>
              </div>
              <div className="text-xs text-gray-400">
                모든 탭은 현재 체크아웃된 스냅샷 상태에서 동작합니다
              </div>
            </div>
          </div>

          {/* Tab navigation */}
          <div className="flex gap-1 mb-4 border-b">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="bg-white rounded-lg shadow">
            {activeTab === "explore" && (
              <DataExplorer
                workspaceId={currentWorkspaceId}
                workspaceApi={WORKSPACE_API}
                currentSnapshot={currentSnapshot}
              />
            )}
            {activeTab === "transform" && (
              <DataSampler
                workspaceId={currentWorkspaceId}
                workspaceApi={WORKSPACE_API}
                currentSnapshot={currentSnapshot}
                onDataChanged={loadSnapshotState}
              />
            )}
            {activeTab === "analysis" && (
              <AnalysisPanel
                workspaceId={currentWorkspaceId}
                workspaceApi={WORKSPACE_API}
                currentSnapshot={currentSnapshot}
              />
            )}
            {activeTab === "experiment" && (
              <ExperimentPanel
                workspaceId={currentWorkspaceId}
                workspaceApi={WORKSPACE_API}
                currentSnapshot={currentSnapshot}
              />
            )}
            {activeTab === "snapshots" && (
              <SnapshotTimeline
                workspaceId={currentWorkspaceId}
                workspaceApi={WORKSPACE_API}
                currentSnapshot={currentSnapshot}
                onSnapshotChange={loadSnapshotState}
              />
            )}
          </div>
        </>
      ) : (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <div className="text-4xl mb-4">📦</div>
          <div className="text-lg font-medium text-gray-700 mb-2">
            워크스페이스를 생성해주세요
          </div>
          <div className="text-sm text-gray-500">
            위의 Base 또는 Target 카드에서 "워크스페이스 생성" 버튼을 클릭하여
            <br />
            데이터 분석, 샘플링, 학습 실험을 시작하세요.
          </div>
        </div>
      )}
    </div>
  );
}
