import React, { useEffect, useState } from "react";

function TreeNode({ node, depth = 0 }) {
  return (
    <div className="ml-2">
      <div className="text-xs">
        <span className="mr-1">{node.children ? "📁" : "📄"}</span>
        {node.name}
      </div>
      {node.children &&
        node.children.map((child) => (
          <TreeNode key={child.name + depth} node={child} depth={depth + 1} />
        ))}
    </div>
  );
}

export default function ZipDetail({ backend, dataset, onBack }) {
  const [eda, setEda] = useState(null);
  const [reportPaths, setReportPaths] = useState(null);

  useEffect(() => {
    fetch(`${backend}/eda/${dataset.id}`)
      .then((r) => r.json())
      .then(setEda);
  }, [backend, dataset]);

  const downloadReport = () => {
    fetch(`${backend}/report/eda/${dataset.id}`)
      .then((r) => r.json())
      .then((info) => {
        setReportPaths(info);
        if (info.pdf) {
          window.open(`${backend}/report/download?path=${encodeURIComponent(info.pdf)}`, "_blank");
        } else if (info.html) {
          window.open(`${backend}/report/download?path=${encodeURIComponent(info.html)}`, "_blank");
        }
      });
  };

  if (!eda) {
    return (
      <div className="max-w-6xl mx-auto">
        <button
          onClick={onBack}
          className="mb-4 px-3 py-2 bg-gray-200 rounded text-xs"
        >
          ← 뒤로
        </button>
        <div className="p-4 text-sm">ZIP EDA 로딩중...</div>
      </div>
    );
  }

  const stats = eda.stats || {};
  const roboflow = eda.roboflow;

  return (
    <div className="max-w-6xl mx-auto">
      <button
        onClick={onBack}
        className="mb-4 px-3 py-2 bg-gray-200 rounded text-xs"
      >
        ← 뒤로
      </button>

      <h2 className="text-xl font-semibold mb-1">
        ZIP Dataset Detail — {dataset.name}
      </h2>
      <div className="text-xs text-gray-500 mb-4">
        Type: {eda.zip_type} · Total files: {stats.total_files ?? 0}
      </div>

      <div className="mb-4 flex gap-3">
        <div className="bg-white rounded shadow p-3 flex-1">
          <div className="text-xs text-gray-500 mb-1">파일 통계</div>
          <div className="text-xs">
            Images: {stats.image_files ?? 0}, Text: {stats.text_files ?? 0},
            CSV: {stats.csv_files ?? 0}, JSON: {stats.json_files ?? 0}, XML:{" "}
            {stats.xml_files ?? 0}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Top-level dirs: {stats.subdirs?.join(", ") || "-"}
          </div>
        </div>

        <div className="bg-white rounded shadow p-3 flex-1">
          <div className="text-xs text-gray-500 mb-1">리포트</div>
          <button
            onClick={downloadReport}
            className="px-3 py-2 bg-blue-600 text-white rounded text-xs"
          >
            ZIP EDA 리포트(PDF/HTML) 다운로드
          </button>
          {reportPaths && (
            <div className="mt-2 text-[10px] text-gray-500">
              HTML: {reportPaths.html}
              <br />
              PDF: {reportPaths.pdf || "생성 실패 또는 미설치(wkhtmltopdf)"}
            </div>
          )}
        </div>
      </div>

      {roboflow && (
        <div className="mb-4 bg-white rounded shadow p-3">
          <div className="text-sm font-semibold mb-2">Roboflow EDA</div>
          <div className="mb-2">
            <div className="text-xs text-gray-500 mb-1">Classes</div>
            <div className="flex flex-wrap gap-1 text-xs">
              {roboflow.classes.map((c) => (
                <span
                  key={c}
                  className="px-2 py-1 bg-gray-100 rounded border text-gray-700"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>

          <div className="text-xs">
            {Object.entries(roboflow.splits).map(([splitName, s]) => (
              <div key={splitName} className="mb-3">
                <div className="font-semibold mb-1">{splitName}</div>
                <div className="mb-1">
                  Images: {s.num_images}, Labels: {s.num_labels}
                </div>
                {s.class_counts && (
                  <div className="ml-2">
                    {Object.entries(s.class_counts).map(([cls, cnt]) => (
                      <div key={cls}>
                        {cls}: {cnt}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded shadow p-3">
        <div className="text-sm font-semibold mb-2">폴더 트리 구조</div>
        {eda.tree ? (
          <div className="max-h-80 overflow-auto border rounded p-2 bg-gray-50">
            <TreeNode node={eda.tree} />
          </div>
        ) : (
          <div className="text-xs text-gray-500">트리 정보 없음</div>
        )}
      </div>
    </div>
  );
}