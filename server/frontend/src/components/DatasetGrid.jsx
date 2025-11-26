import React, { useState } from "react";

export default function DatasetGrid({
  datasets,
  backend,
  refresh,
  onSelect,
  onEDA,
  onDrift,
}) {
  const [file, setFile] = useState(null);
  const [page, setPage] = useState(1);
  const pageSize = 8;

  const upload = () => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);

    fetch(`${backend}/datasets/upload`, {
      method: "POST",
      body: form,
    })
      .then(() => {
        setFile(null);
        refresh();
      })
      .catch((e) => console.error("Upload failed", e));
  };

  const totalPages = Math.max(1, Math.ceil(datasets.length / pageSize));
  const start = (page - 1) * pageSize;
  const pageData = datasets.slice(start, start + pageSize);

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      {/* 상단 헤더 + 업로드 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">데이터셋 워크스페이스</h2>
          <p className="text-xs text-gray-500">
            업로드된 데이터셋을 카드 형태로 관리하고, 선택해서 EDA/Drift 분석을 수행합니다.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-xs"
          />
          <button
            onClick={upload}
            disabled={!file}
            className="px-3 py-2 bg-blue-600 text-white rounded-md text-xs disabled:bg-gray-300"
          >
            업로드
          </button>
        </div>
      </div>

      {/* 카드 그리드 */}
      <div className="grid grid-cols-4 gap-4">
        {pageData.map((ds) => {
          const typeLabel = (ds.type || "").toUpperCase();
          const preview = ds.preview || {};
          const head = preview.head;
          const firstLines = preview.first_lines;
          const thumb = preview.thumbnail;

          return (
            <div
              key={ds.id}
              className="bg-white border border-gray-200 rounded-lg shadow-sm p-3 flex flex-col hover:shadow-md transition cursor-pointer"
              onClick={() => onSelect && onSelect(ds)}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] px-2 py-1 bg-gray-100 rounded-full text-gray-600">
                  {typeLabel || "UNKNOWN"}
                </span>
                <span className="text-[10px] text-gray-400">
                  {ds.rows} rows · {ds.cols} cols
                </span>
              </div>

              <div className="font-semibold text-sm truncate mb-2">
                {ds.name}
              </div>

              {/* 썸네일 / 미리보기 */}
              {thumb ? (
                <div className="mb-2">
                  {/* 백엔드 다운로드 엔드포인트를 재사용 */}
                  <img
                    src={`${backend}/files/raw?path=${encodeURIComponent(
                      thumb
                    )}`}
                    alt="thumbnail"
                    className="w-full h-24 object-cover rounded"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect && onSelect(ds);
                    }}
                  />
                </div>
              ) : null}

              {head && (
                <div className="flex-1 bg-gray-50 rounded p-1 mb-2 overflow-hidden">
                  <div className="text-[10px] text-gray-400 mb-1">
                    preview (row 1)
                  </div>
                  <pre className="text-[10px] whitespace-pre-wrap">
                    {JSON.stringify(head[0], null, 0).slice(0, 80)}…
                  </pre>
                </div>
              )}

              {firstLines && !head && (
                <div className="flex-1 bg-gray-50 rounded p-1 mb-2 overflow-hidden">
                  <div className="text-[10px] text-gray-400 mb-1">
                    preview (text)
                  </div>
                  <pre className="text-[10px] whitespace-pre-wrap">
                    {firstLines.join("\n").slice(0, 80)}…
                  </pre>
                </div>
              )}

              <div className="flex gap-1 mt-auto">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onEDA && onEDA(ds);
                  }}
                  className="flex-1 px-2 py-1 text-[11px] bg-green-600 text-white rounded"
                >
                  EDA
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDrift && onDrift(ds);
                  }}
                  className="flex-1 px-2 py-1 text-[11px] bg-purple-600 text-white rounded"
                >
                  Drift
                </button>
              </div>
            </div>
          );
        })}

        {pageData.length === 0 && (
          <div className="col-span-4 text-sm text-gray-400">
            아직 업로드된 데이터셋이 없습니다.
          </div>
        )}
      </div>

      {/* 페이지네이션 */}
      <div className="flex justify-center gap-2 text-xs">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          className="px-2 py-1 border rounded disabled:opacity-50"
          disabled={page === 1}
        >
          이전
        </button>
        <span className="px-2 py-1">
          {page} / {totalPages}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          className="px-2 py-1 border rounded disabled:opacity-50"
          disabled={page === totalPages}
        >
          다음
        </button>
      </div>
    </div>
  );
}
