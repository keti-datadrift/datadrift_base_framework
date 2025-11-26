import React, { useState } from "react";

export default function DatasetGrid({ datasets, backend, refresh, onEDA, onDrift }) {
  const [file, setFile] = useState(null);
  const [page, setPage] = useState(1);
  const pageSize = 8;

  const upload = () => {
    const form = new FormData();
    form.append("file", file);

    fetch(`${backend}/datasets/upload`, {
      method: "POST",
      body: form,
    }).then(() => {
      setFile(null);
      refresh();
    });
  };

  const totalPages = Math.max(1, Math.ceil(datasets.length / pageSize));
  const start = (page - 1) * pageSize;
  const pageData = datasets.slice(start, start + pageSize);

  return (
    <div className="max-w-6xl mx-auto">
      {/* 업로드 영역 */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold">데이터셋 목록</h2>
        <div className="flex gap-2">
          <input
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
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
      <div className="grid grid-cols-4 gap-4 mb-4">
        {pageData.map((ds) => (
          <div
            key={ds.id}
            className="bg-white border border-gray-200 rounded-lg shadow-sm p-3 flex flex-col"
          >
            <div className="text-xs text-gray-400 mb-1">
              {ds.type?.toUpperCase()}
            </div>
            <div className="font-semibold text-sm truncate mb-1">
              {ds.name}
            </div>
            <div className="text-[11px] text-gray-500 mb-2">
              {ds.rows} rows · {ds.cols} cols
            </div>

            {/* preview (csv일 때만) */}
            {ds.preview?.head && (
              <div className="flex-1 bg-gray-50 rounded p-1 mb-2 overflow-hidden">
                <div className="text-[10px] text-gray-400 mb-1">preview</div>
                <pre className="text-[10px] whitespace-pre-wrap">
                  {JSON.stringify(ds.preview.head[0], null, 0).slice(0, 80)}…
                </pre>
              </div>
            )}
              
            {ds.preview?.thumbnail && (
              <img
                src={`${backend}/report/download?path=${ds.preview.thumbnail}`}
                alt="thumb"
                className="w-full h-32 object-cover rounded"
              />
            )}
              
            <div className="flex gap-1 mt-auto">
              <button
                onClick={() => onEDA(ds)}
                className="flex-1 px-2 py-1 text-[11px] bg-green-600 text-white rounded"
              >
                EDA
              </button>
              <button
                onClick={() => onDrift(ds)}
                className="flex-1 px-2 py-1 text-[11px] bg-purple-600 text-white rounded"
              >
                Drift
              </button>
            </div>
          </div>
        ))}

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