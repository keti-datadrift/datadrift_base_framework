import React, { useState } from "react";

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
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold">{title}</h2>

        {!driftMode && (
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
        )}

        {driftMode && (
          <button
            className="px-4 py-2 bg-gray-500 text-white rounded"
            onClick={onBack}
          >
            ← 뒤로가기
          </button>
        )}
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
              onClick={() => !driftMode && onSelect && onSelect(ds)}
            >
              {/* 타입 뱃지 */}
              <div className="text-[10px] text-gray-500 mb-1">{badge}</div>

              {/* 썸네일 */}
              {hasThumb && (
                <div className="mb-2">
                  <img
                    src={`${backend}/files/raw?path=${encodeURIComponent(
                      ds.preview.thumbnail
                    )}`}
                    alt="thumb"
                    className="w-full h-24 object-cover rounded-md border border-gray-100"
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
              <div className="flex-1 text-[11px] text-gray-600 mb-2">
                {/* CSV */}
                {ds.type === "csv" && ds.preview?.head && (
                  <pre className="whitespace-pre-wrap">
                    {JSON.stringify(ds.preview.head[0], null, 0).slice(0, 80)}…
                  </pre>
                )}
                {/* TEXT */}
                {ds.type === "text" && ds.preview?.first_lines && (
                  <pre className="whitespace-pre-wrap">
                    {ds.preview.first_lines.join(" ").slice(0, 80)}…
                  </pre>
                )}
                {/* ZIP */}
                {ds.type === "zip" && (
                  <div>
                    <div className="font-semibold text-[11px] mb-1">
                      ZIP / {ds.preview?.zip_type}
                    </div>
                    {ds.preview?.tree && (
                      <div className="text-[10px] text-gray-500 mt-1">
                        {ds.preview.tree.children?.map((c) => (
                          <div key={c.name}>📁 {c.name}</div>
                        ))}
                      </div>
                    )}
                    <div className="text-[10px] text-gray-500 mt-1">
                      files: {ds.preview?.stats?.total_files ?? 0}, images:{" "}
                      {ds.preview?.stats?.image_files ?? 0}
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

              {/* 액션 버튼 */}
              <div className="flex gap-1 mt-auto">
                {!driftMode && (
                  <>
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
                  </>
                )}

                {driftMode && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectTarget(ds);
                    }}
                    disabled={ds.id === compareBase?.id}
                    className="flex-1 px-2 py-1 text-[11px] bg-blue-600 text-white rounded disabled:bg-gray-300"
                  >
                    이 데이터셋과 비교하기
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 페이지네이션 */}
      <div className="flex justify-center gap-2 text-xs">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          className="px-2 py-1 border rounded disabled:opacity-50"
        >
          이전
        </button>
        <span className="px-2 py-1">
          {page} / {totalPages}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page === totalPages}
          className="px-2 py-1 border rounded disabled:opacity-50"
        >
          다음
        </button>
      </div>
    </div>
  );
}