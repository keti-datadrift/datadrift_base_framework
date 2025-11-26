import React, { useState } from "react";

export default function DatasetGrid({ datasets, backend, refresh, onEDA, onDrift, onSelect }) {
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

  return (
    <div className="max-w-6xl mx-auto">
      {/* 업로드 영역 */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold">데이터셋 목록</h2>
        <div className="flex gap-2 items-center">
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
        {pageData.map((ds) => {
          const hasThumb = ds.preview && ds.preview.thumbnail;
          const badge = typeLabel(ds.type, ds.preview);

          return (
            <div
              key={ds.id}
              className="bg-white border border-gray-200 rounded-lg shadow-sm p-3 flex flex-col cursor-pointer hover:border-blue-400 transition"
              onClick={() => onSelect && onSelect(ds)}
            >
              {/* 타입 뱃지 */}
              <div className="text-[10px] text-gray-500 mb-1">
                {badge}
              </div>

              {/* 썸네일 (이미지/ZIP 공통) */}
              {hasThumb && (
                <div className="mb-2">
                  <img
                    src={`${backend}/files/raw?path=${encodeURIComponent(
                      ds.preview.thumbnail
                    )}`}
                    alt="thumb"
                    className="w-full h-24 object-cover rounded-md border border-gray-100"
                    onClick={(e) => {
                      e.stopPropagation(); // 카드 클릭으로 Detail로 가는 것과 분리
                    }}
                  />
                </div>
              )}

              {/* 이름 / 기본정보 */}
              <div className="font-semibold text-sm truncate mb-1">
                {ds.name}
              </div>
              <div className="text-[11px] text-gray-500 mb-2">
                {ds.rows ?? 0} rows · {ds.cols ?? 0} cols
              </div>

              {/* 프리뷰 텍스트 */}
              <div className="flex-1 text-[11px] text-gray-600 mb-2">
                {ds.type === "csv" && ds.preview?.head && (
                  <pre className="whitespace-pre-wrap">
                    {JSON.stringify(ds.preview.head[0], null, 0).slice(0, 80)}…
                  </pre>
                )}

                {ds.type === "text" && ds.preview?.first_lines && (
                  <pre className="whitespace-pre-wrap">
                    {ds.preview.first_lines.join(" ").slice(0, 80)}…
                  </pre>
                )}

                {ds.type === "zip" && (
                  <div>
                    <div className="font-semibold text-[11px] mb-1">
                      ZIP / {ds.preview?.zip_type}
                    </div>
                
                    {/* Tree View: 상위 디렉토리만 요약 표시 */}
                    {ds.preview?.tree && (
                      <div className="text-[10px] text-gray-500 mt-1">
                        {ds.preview.tree.children?.map((c) => (
                          <div key={c.name}>📁 {c.name}</div>
                        ))}
                      </div>
                    )}
                
                    {/* 파일 개수 정보 */}
                    <div className="text-[10px] text-gray-500 mt-1">
                      files: {ds.preview?.stats?.total_files ?? 0}, images:{" "}
                      {ds.preview?.stats?.image_files ?? 0}
                    </div>
                  </div>
                )}

                {!["csv", "text", "zip"].includes(ds.type) && (
                  <div className="text-[11px] text-gray-400">
                    {ds.preview?.info || "미리보기 없음"}
                  </div>
                )}
              </div>

              {/* 액션 버튼들 */}
              <div className="flex gap-1 mt-auto">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onEDA(ds);
                  }}
                  className="flex-1 px-2 py-1 text-[11px] bg-green-600 text-white rounded"
                >
                  EDA
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDrift(ds);
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