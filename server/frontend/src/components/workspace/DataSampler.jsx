import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";

/**
 * DataSampler - Data transformation, sampling, and export with FiftyOne integration
 */
export default function DataSampler({ workspaceId, workspaceApi, currentSnapshot, onDataChanged }) {
  const [stats, setStats] = useState(null);
  const [views, setViews] = useState([]);
  const [samples, setSamples] = useState([]);
  const [exports, setExports] = useState([]);
  const [exportFormats, setExportFormats] = useState([]);
  const [loading, setLoading] = useState(true);

  // View-based transformation form
  const [selectedView, setSelectedView] = useState("");
  const [operation, setOperation] = useState("keep_only");
  const [snapshotMessage, setSnapshotMessage] = useState("");
  const [snapshotAlias, setSnapshotAlias] = useState("");
  const [preview, setPreview] = useState(null);
  const [applying, setApplying] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Sampling form
  const [strategy, setStrategy] = useState("random");
  const [sampleName, setSampleName] = useState("");
  const [sampleN, setSampleN] = useState(100);
  const [creating, setCreating] = useState(false);

  // Export form
  const [exportFormat, setExportFormat] = useState("yolo");
  const [exporting, setExporting] = useState(false);

  // Load data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      
      const [statsRes, viewsRes, samplesRes, exportsRes, formatsRes] = await Promise.all([
        axios.get(`${workspaceApi}/workspace/${workspaceId}/data/stats`).catch(() => ({ data: {} })),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/fiftyone/views`).catch(() => ({ data: { views: [] } })),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/data/samples`).catch(() => ({ data: { samples: [] } })),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/data/exports`).catch(() => ({ data: { exports: [] } })),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/data/export/formats`).catch(() => ({ data: { formats: [] } })),
      ]);
      
      setStats(statsRes.data);
      setViews(viewsRes.data.views || []);
      setSamples(samplesRes.data.samples || []);
      setExports(exportsRes.data.exports || []);
      setExportFormats(formatsRes.data.formats || [
        { id: "yolo", name: "YOLO", description: "YOLO 형식" },
        { id: "coco", name: "COCO", description: "COCO JSON 형식" },
      ]);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, workspaceApi]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Preview transformation
  const loadPreview = async () => {
    if (!selectedView) return;
    
    try {
      setPreviewLoading(true);
      const response = await axios.post(
        `${workspaceApi}/workspace/${workspaceId}/data/preview-transform`,
        {
          view_name: selectedView,
          operation: operation,
          snapshot_message: snapshotMessage || "Preview",
          dry_run: true,
        }
      );
      setPreview(response.data);
    } catch (err) {
      console.error("Failed to load preview:", err);
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Apply transformation
  const applyTransformation = async () => {
    if (!selectedView) {
      alert("View를 선택해주세요");
      return;
    }
    if (!snapshotMessage.trim()) {
      alert("스냅샷 메시지를 입력해주세요");
      return;
    }

    if (!confirm(`${operation === "keep_only" ? "선택한 View의 데이터만 유지" : "선택한 View의 데이터 삭제"}하시겠습니까?\n이 작업은 되돌릴 수 없으며, 자동으로 스냅샷이 생성됩니다.`)) {
      return;
    }

    try {
      setApplying(true);
      
      const response = await axios.post(
        `${workspaceApi}/workspace/${workspaceId}/data/apply-view`,
        {
          view_name: selectedView,
          operation: operation,
          snapshot_message: snapshotMessage,
          snapshot_alias: snapshotAlias || null,
          dry_run: false,
        }
      );

      alert(`✅ ${response.data.message}`);
      
      // Reset form
      setSelectedView("");
      setSnapshotMessage("");
      setSnapshotAlias("");
      setPreview(null);
      
      // Reload data and notify parent
      loadData();
      if (onDataChanged) {
        onDataChanged();
      }
    } catch (err) {
      console.error("Failed to apply transformation:", err);
      alert(err.response?.data?.detail || "데이터 변형 실패");
    } finally {
      setApplying(false);
    }
  };

  // Create sample
  const createSample = async () => {
    if (!sampleName.trim()) {
      alert("샘플 이름을 입력해주세요");
      return;
    }

    try {
      setCreating(true);
      
      const params = { n: sampleN };
      if (strategy === "stratified") {
        params.seed = 42;
      }

      await axios.post(`${workspaceApi}/workspace/${workspaceId}/data/sample`, {
        strategy,
        params,
        output_name: sampleName,
      });

      setSampleName("");
      loadData();
    } catch (err) {
      console.error("Failed to create sample:", err);
      alert("샘플 생성 실패");
    } finally {
      setCreating(false);
    }
  };

  // Export dataset
  const exportDataset = async () => {
    try {
      setExporting(true);
      
      await axios.post(`${workspaceApi}/workspace/${workspaceId}/data/export`, {
        format: exportFormat,
      });

      loadData();
    } catch (err) {
      console.error("Failed to export:", err);
      alert("내보내기 실패");
    } finally {
      setExporting(false);
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
          📍 현재 스냅샷: <strong>{currentSnapshot || "초기 상태"}</strong>
          <span className="ml-2 text-blue-500">
            - 변형 작업은 이 상태에서 수행됩니다
          </span>
        </span>
      </div>

      {/* Data Transformation Section (Main) */}
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
        <h3 className="font-semibold mb-4 text-purple-800">✂️ 데이터 변형 (View 기반)</h3>
        
        <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
            <label className="block text-sm font-medium mb-1">FiftyOne View 선택</label>
            <select
              value={selectedView}
              onChange={(e) => {
                setSelectedView(e.target.value);
                setPreview(null);
              }}
              className="w-full px-3 py-2 border rounded"
            >
              <option value="">View 선택...</option>
              {views.map((view) => (
                <option key={view.name} value={view.name}>
                  {view.name}
                </option>
              ))}
            </select>
            {views.length === 0 && (
              <div className="text-xs text-gray-500 mt-1">
                데이터 탐색 탭에서 FiftyOne으로 필터링 후 View를 저장하세요
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">작업 유형</label>
            <select
              value={operation}
              onChange={(e) => {
                setOperation(e.target.value);
                setPreview(null);
              }}
              className="w-full px-3 py-2 border rounded"
            >
              <option value="keep_only">View 데이터만 유지</option>
              <option value="remove">View 데이터 삭제</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
            <label className="block text-sm font-medium mb-1">스냅샷 메시지 *</label>
              <input
                type="text"
              value={snapshotMessage}
              onChange={(e) => setSnapshotMessage(e.target.value)}
              placeholder="예: 노이즈 데이터 제거"
                className="w-full px-3 py-2 border rounded"
              />
            </div>
            <div>
            <label className="block text-sm font-medium mb-1">스냅샷 별칭 (선택)</label>
            <input
              type="text"
              value={snapshotAlias}
              onChange={(e) => setSnapshotAlias(e.target.value)}
              placeholder="예: clean_v1"
                className="w-full px-3 py-2 border rounded"
            />
          </div>
        </div>

        {/* Preview */}
        <div className="mb-4 flex items-center gap-4">
          <button
            onClick={loadPreview}
            disabled={!selectedView || previewLoading}
            className="px-4 py-2 bg-gray-100 border rounded text-sm hover:bg-gray-200 disabled:opacity-50"
          >
            {previewLoading ? "로딩..." : "🔍 미리보기"}
          </button>
          
          {preview && (
            <div className="flex-1 p-3 bg-white border rounded flex items-center justify-around">
              <div className="text-center">
                <div className="text-xl font-bold text-red-600">{preview.files_to_remove}</div>
                <div className="text-xs text-gray-500">삭제</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-green-600">{preview.files_to_keep}</div>
                <div className="text-xs text-gray-500">유지</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-gray-600">{stats?.total_items || 0}</div>
                <div className="text-xs text-gray-500">현재</div>
              </div>
            </div>
          )}
        </div>

        <button
          onClick={applyTransformation}
          disabled={!selectedView || !snapshotMessage.trim() || applying}
          className="w-full px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 font-medium"
        >
          {applying ? "적용 중..." : "🚀 변경 적용 & 스냅샷 생성"}
        </button>

        <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
          ⚠️ 데이터 변형 시 자동으로 스냅샷이 생성됩니다. 이전 상태로 체크아웃 가능합니다.
        </div>
      </div>

      {/* Stats and Sampling/Export (Side by side) */}
      <div className="grid grid-cols-3 gap-6">
        {/* Stats */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium mb-3">📊 현재 데이터셋</h4>
          <div className="text-3xl font-bold">{stats?.total_items || 0}</div>
          <div className="text-sm text-gray-500">{stats?.total_size_mb || 0} MB</div>
          <div className="mt-3 text-xs text-gray-400">
            포맷: {stats?.format || "N/A"}
          </div>
            </div>

        {/* Sampling */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium mb-3">📋 샘플링</h4>
          <div className="space-y-2">
            <input
              type="text"
              value={sampleName}
              onChange={(e) => setSampleName(e.target.value)}
              placeholder="샘플 이름"
              className="w-full px-2 py-1 border rounded text-sm"
            />
            <div className="flex gap-2">
              <input
                type="number"
                value={sampleN}
                onChange={(e) => setSampleN(parseInt(e.target.value) || 100)}
                className="w-20 px-2 py-1 border rounded text-sm"
              />
            <button
              onClick={createSample}
                disabled={creating || !sampleName.trim()}
                className="flex-1 px-2 py-1 bg-blue-500 text-white rounded text-sm disabled:opacity-50"
            >
                {creating ? "..." : "생성"}
                    </button>
            </div>
          </div>
        </div>

        {/* Export */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium mb-3">📤 내보내기</h4>
          <div className="space-y-2">
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
              className="w-full px-2 py-1 border rounded text-sm"
              >
                {exportFormats.map((fmt) => (
                <option key={fmt.id} value={fmt.id}>{fmt.name}</option>
                ))}
              </select>
            <button
              onClick={exportDataset}
              disabled={exporting}
              className="w-full px-2 py-1 bg-green-500 text-white rounded text-sm disabled:opacity-50"
            >
              {exporting ? "..." : "내보내기"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
