import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";

/**
 * DataExplorer - Browse and preview dataset items with FiftyOne integration
 */
export default function DataExplorer({ workspaceId, workspaceApi, currentSnapshot }) {
  // Grid view state - Commented out: using FiftyOne only
  /*
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [splitFilter, setSplitFilter] = useState("");
  const [classFilter, setClassFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const limit = 24;
  const [selectedItem, setSelectedItem] = useState(null);
  const [preview, setPreview] = useState(null);
  */
  
  // FiftyOne state
  const [fiftyoneStatus, setFiftyoneStatus] = useState(null);
  const [fiftyoneUrl, setFiftyoneUrl] = useState(null);

  // Grid view functions - Commented out: using FiftyOne only
  /*
  // Load items
  const loadItems = useCallback(async () => {
    try {
      setLoading(true);
      
      const params = { limit, offset };
      if (splitFilter) params.split = splitFilter;
      if (classFilter) params.class_filter = classFilter;
      
      const response = await axios.get(
        `${workspaceApi}/workspace/${workspaceId}/data/items`,
        { params }
      );
      
      setItems(response.data.items);
      setTotal(response.data.total);
    } catch (err) {
      console.error("Failed to load items:", err);
      setError("데이터 로딩 실패");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, workspaceApi, offset, splitFilter, classFilter]);

  // Load stats
  const loadStats = useCallback(async () => {
    try {
      const response = await axios.get(
        `${workspaceApi}/workspace/${workspaceId}/data/stats`
      );
      setStats(response.data);
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
  }, [workspaceId, workspaceApi]);
  */

  // Auto-load FiftyOne dataset on mount
  const loadFiftyoneDataset = useCallback(async () => {
    try {
      console.log(`[FiftyOne] 워크스페이스 ${workspaceId} 데이터셋 자동 로드 시작...`);
      const loadRes = await axios.post(
        `${workspaceApi}/workspace/${workspaceId}/fiftyone/load`,
        {}
      );
      console.log("[FiftyOne] 데이터셋 로드 성공:", loadRes.data);
      
      // After loading, check status and get URL
      await checkFiftyoneStatus();
    } catch (err) {
      console.error("[FiftyOne] 데이터셋 로드 실패:", err);
      // Don't throw - FiftyOne is optional
    }
  }, [workspaceId, workspaceApi]);

  // Check FiftyOne status
  const checkFiftyoneStatus = useCallback(async () => {
    try {
      const [statusRes, urlRes] = await Promise.all([
        axios.get(`${workspaceApi}/workspace/${workspaceId}/fiftyone/status`).catch(() => null),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/fiftyone/url`).catch(() => null),
      ]);
      
      if (statusRes?.data) {
        setFiftyoneStatus(statusRes.data);
        console.log("[FiftyOne] 상태:", statusRes.data);
      }
      if (urlRes?.data) {
        setFiftyoneUrl(urlRes.data.url);
        console.log("[FiftyOne] URL:", urlRes.data.url);
      }
    } catch (err) {
      console.error("Failed to check FiftyOne status:", err);
    }
  }, [workspaceId, workspaceApi]);

  useEffect(() => {
    // loadItems();  // Commented out - using FiftyOne only
    // loadStats();  // Commented out - using FiftyOne only
    
    // Auto-load FiftyOne dataset
    loadFiftyoneDataset();
  }, [loadFiftyoneDataset]);

  /*
  // Load item preview
  const loadPreview = async (item) => {
    setSelectedItem(item);
    try {
      const response = await axios.get(
        `${workspaceApi}/workspace/${workspaceId}/data/item/${item.id}/preview`
      );
      setPreview(response.data);
    } catch (err) {
      console.error("Failed to load preview:", err);
    }
  };

  // Pagination
  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;
  */

  return (
    <div className="p-4">
      {/* View mode toggle - Commented out: using FiftyOne only */}
      {/* 
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode("grid")}
            className={`px-4 py-2 rounded text-sm font-medium transition ${
              viewMode === "grid"
                ? "bg-blue-500 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            🔲 그리드 뷰
          </button>
          <button
            onClick={() => setViewMode("fiftyone")}
            disabled={!fiftyoneStatus?.available}
            className={`px-4 py-2 rounded text-sm font-medium transition ${
              viewMode === "fiftyone"
                ? "bg-purple-500 text-white"
                : fiftyoneStatus?.available
                ? "bg-gray-100 text-gray-700 hover:bg-gray-200"
                : "bg-gray-100 text-gray-400 cursor-not-allowed"
            }`}
            title={fiftyoneStatus?.available ? "FiftyOne으로 탐색" : "FiftyOne 서버가 실행되지 않았습니다"}
          >
            🔍 FiftyOne 뷰
            {!fiftyoneStatus?.available && " (비활성)"}
          </button>
        </div>
        {currentSnapshot && (
          <div className="text-sm text-gray-500">
            📍 스냅샷: <strong>{currentSnapshot}</strong>
          </div>
        )}
      </div>
      */}

      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-700">🔍 FiftyOne 데이터셋 탐색기</h2>
        {currentSnapshot && (
          <div className="text-sm text-gray-500">
            📍 스냅샷: <strong>{currentSnapshot}</strong>
          </div>
        )}
      </div>

      {/* FiftyOne View */}
      {fiftyoneUrl ? (
        <div className="mb-4">
          <div className="bg-gray-100 rounded-lg overflow-hidden border shadow-sm">
            <div className="p-2 bg-gray-200 text-xs text-gray-600 flex items-center justify-between">
              <span>
                {fiftyoneStatus?.current_dataset && (
                  <span className="font-medium mr-2">
                    {fiftyoneStatus.sample_count?.toLocaleString()} samples
                  </span>
                )}
                Dataset: {fiftyoneStatus?.current_dataset || 'Loading...'}
              </span>
              <a
                href={fiftyoneUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                새 탭에서 열기 ↗
              </a>
            </div>
            <iframe
              src={fiftyoneUrl}
              className="w-full border-0"
              style={{ height: "calc(100vh - 200px)", minHeight: "800px" }}
              title="FiftyOne Dataset Explorer"
            />
          </div>
          <div className="mt-2 p-3 bg-blue-50 rounded text-sm text-blue-800">
            💡 FiftyOne에서 필터링하고 View를 저장한 후, "데이터 변형" 탭에서 변경을 적용하세요.
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin h-8 w-8 border-3 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-600">FiftyOne 데이터셋 로딩 중...</p>
          </div>
        </div>
      )}

      {/* Grid View - Removed: using FiftyOne only
      
      All grid view code has been commented out as we're using FiftyOne exclusively.
      If needed in the future, restore from git history.
      
      Previous features:
      - Stats header showing total items, size, format, class count
      - Filters for split and class
      - Image grid with thumbnails
      - Pagination controls
      - Preview modal with image details
      
      */}
      
      {/* Old grid view code removed - see git history to restore */}
      {false && (
        <>
          {/* Stats header */}
          {stats && (
            <div className="mb-4 grid grid-cols-4 gap-4">
              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500">총 아이템</div>
                <div className="text-xl font-bold">{stats.total_items}</div>
              </div>
              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500">데이터 크기</div>
                <div className="text-xl font-bold">{stats.total_size_mb} MB</div>
              </div>
              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500">포맷</div>
                <div className="text-xl font-bold">{stats.format}</div>
              </div>
              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500">클래스 수</div>
                <div className="text-xl font-bold">{Object.keys(stats.classes || {}).length}</div>
              </div>
            </div>
          )}

      {/* Filters */}
      <div className="mb-4 flex gap-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Split</label>
          <select
            value={splitFilter}
            onChange={(e) => { setSplitFilter(e.target.value); setOffset(0); }}
            className="px-3 py-2 border rounded text-sm"
          >
            <option value="">전체</option>
            {stats?.splits && Object.keys(stats.splits).map((split) => (
              <option key={split} value={split}>
                {split} ({stats.splits[split]})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Class</label>
          <select
            value={classFilter}
            onChange={(e) => { setClassFilter(e.target.value); setOffset(0); }}
            className="px-3 py-2 border rounded text-sm"
          >
            <option value="">전체</option>
            {stats?.classes && Object.keys(stats.classes).map((cls) => (
              <option key={cls} value={cls}>
                {cls} ({stats.classes[cls]})
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1"></div>
        <div className="flex items-end">
          <span className="text-sm text-gray-500">
            {total}개 중 {offset + 1}-{Math.min(offset + limit, total)}
          </span>
        </div>
      </div>

      {/* Loading / Error */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded">{error}</div>
      )}

      {/* Image grid */}
      {!loading && !error && (
        <div className="grid grid-cols-6 gap-3">
          {items.map((item) => (
            <div
              key={item.id}
              className={`aspect-square bg-gray-100 rounded overflow-hidden cursor-pointer border-2 transition ${
                selectedItem?.id === item.id ? "border-blue-500" : "border-transparent hover:border-gray-300"
              }`}
              onClick={() => loadPreview(item)}
            >
              <img
                src={`${workspaceApi}/workspace/${workspaceId}/data/item/${item.id}/thumbnail?size=150`}
                alt={item.filename}
                className="w-full h-full object-cover"
                loading="lazy"
                onError={(e) => {
                  e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23f0f0f0' width='100' height='100'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999' font-size='12'%3ENo Image%3C/text%3E%3C/svg%3E";
                }}
              />
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="px-3 py-1 bg-gray-100 rounded text-sm disabled:opacity-50"
          >
            이전
          </button>
          <span className="text-sm text-gray-500">
            {currentPage} / {totalPages}
          </span>
          <button
            onClick={() => setOffset(offset + limit)}
            disabled={offset + limit >= total}
            className="px-3 py-1 bg-gray-100 rounded text-sm disabled:opacity-50"
          >
            다음
          </button>
        </div>
      )}

          {/* Preview modal */}
          {selectedItem && preview && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedItem(null)}>
              <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
                <div className="p-4 border-b flex items-center justify-between">
                  <h3 className="font-semibold">{preview.filename}</h3>
                  <button onClick={() => setSelectedItem(null)} className="text-gray-500 hover:text-gray-700">✕</button>
                </div>
                <div className="p-4">
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <img
                        src={`${workspaceApi}/workspace/${workspaceId}/data/item/${selectedItem.id}/image`}
                        alt={preview.filename}
                        className="w-full rounded"
                      />
                    </div>
                    <div className="w-64">
                      <h4 className="font-medium mb-2">정보</h4>
                      <div className="text-sm space-y-1">
                        <div><span className="text-gray-500">ID:</span> {preview.id}</div>
                        <div><span className="text-gray-500">Split:</span> {preview.split || "N/A"}</div>
                        <div><span className="text-gray-500">크기:</span> {preview.width}x{preview.height}</div>
                        <div><span className="text-gray-500">파일 크기:</span> {(preview.size_bytes / 1024).toFixed(1)} KB</div>
                        {preview.classes && preview.classes.length > 0 && (
                          <div><span className="text-gray-500">클래스:</span> {preview.classes.join(", ")}</div>
                        )}
                      </div>
                      {preview.label_content && (
                        <div className="mt-4">
                          <h4 className="font-medium mb-2">라벨</h4>
                          <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">
                            {preview.label_content}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
