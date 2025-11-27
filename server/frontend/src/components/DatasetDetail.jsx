import React from "react";

export default function DatasetDetail({
  backend,
  dataset,
  onBack,
  onOpenEDA,
  onOpenDrift,
}) {
  const preview = dataset.preview || {};
  const head = preview.head;
  const firstLines = preview.first_lines;
  const thumb = preview.thumbnail;

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <button
        onClick={onBack}
        className="px-3 py-2 bg-gray-200 rounded text-xs"
      >
        ← 목록으로
      </button>

      <div className="bg-white rounded shadow p-4 flex gap-4">
        {thumb && (
          <div className="w-40 h-40 flex-shrink-0">
            <img
              src={`${backend}/files/raw?path=${encodeURIComponent(
                thumb
              )}`}
              alt="thumbnail"
              className="w-full h-full object-cover rounded"
            />
          </div>
        )}

        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs px-2 py-1 bg-gray-100 rounded-full text-gray-600">
              {(dataset.type || "").toUpperCase()}
            </span>
            <span className="text-lg font-semibold">{dataset.name}</span>
          </div>
          <div className="text-xs text-gray-500">
            {dataset.rows} rows · {dataset.cols} cols
          </div>

          <div className="flex gap-2 mt-2">
            <button
              onClick={onOpenEDA}
              className="px-3 py-2 bg-green-600 text-white rounded text-xs"
            >
              EDA Studio 열기
            </button>
            <button
              onClick={onOpenDrift}
              className="px-3 py-2 bg-purple-600 text-white rounded text-xs"
            >
              Drift Studio 열기
            </button>
            <button
              onClick={() => {
                fetch(`${backend}/report/eda/${dataset.id}`)
                  .then((r) => r.json())
                  .then((info) => {
                    if (info.html) {
                      window.open(
                        `${backend}/report/download?path=${encodeURIComponent(
                          info.html
                        )}`,
                        "_blank"
                      );
                    }
                  });
              }}
              className="px-3 py-2 bg-blue-600 text-white rounded text-xs"
            >
              EDA 리포트 (HTML)
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <h3 className="text-sm font-semibold mb-2">데이터 미리보기</h3>
        {head && (
          <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-64">
            {JSON.stringify(head, null, 2)}
          </pre>
        )}
        {firstLines && !head && (
          <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-64 whitespace-pre-wrap">
            {firstLines.join("\n")}
          </pre>
        )}
        {!head && !firstLines && (
          <div className="text-xs text-gray-400">미리보기 정보가 없습니다.</div>
        )}
      </div>
    </div>
  );
}
