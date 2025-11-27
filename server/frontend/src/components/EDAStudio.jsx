import React, { useEffect, useState } from "react";

export default function EDAStudio({ backend, dataset, onBack }) {
  const [eda, setEda] = useState(null);

  useEffect(() => {
    fetch(`${backend}/eda/${dataset.id}`)
      .then((r) => r.json())
      .then(setEda);
  }, [backend, dataset]);

  if (!eda) {
    return (
      <div className="p-4">
        <button
          onClick={onBack}
          className="mb-2 px-3 py-2 bg-gray-200 rounded text-xs"
        >
          ← 뒤로
        </button>
        <div className="text-sm">EDA 로딩 중...</div>
      </div>
    );
  }

  const type = eda.type || dataset.type;

  return (
    <div className="max-w-5xl mx-auto p-4">
      <button
        onClick={onBack}
        className="mb-3 px-3 py-2 bg-gray-200 rounded text-xs"
      >
        ← 뒤로
      </button>

      <h2 className="text-xl font-semibold mb-1">
        EDA — {dataset.name}
      </h2>
      <div className="text-xs text-gray-500 mb-4">Type: {type}</div>

      {/* ------------------------------------------------------ */}
      {/* CSV 전용 뷰 */}
      {/* ------------------------------------------------------ */}
      {type === "csv" && (
        <div className="space-y-4">
          {/* Shape */}
          {eda.shape && (
            <div className="bg-white rounded shadow p-3">
              <div className="font-semibold text-sm mb-2">Shape</div>
              <div className="text-xs">
                Rows: {eda.shape[0]}, Cols: {eda.shape[1]}
              </div>
            </div>
          )}

          {/* Missing rate */}
          {eda.missing_rate && (
            <div className="bg-white rounded shadow p-3">
              <div className="font-semibold text-sm mb-2">Missing Rate</div>
              <pre className="text-xs">
                {JSON.stringify(eda.missing_rate, null, 2)}
              </pre>
            </div>
          )}

          {/* Summary */}
          {eda.summary && (
            <div className="bg-white rounded shadow p-3">
              <div className="font-semibold text-sm mb-2">Summary</div>
              <pre className="text-xs">
                {JSON.stringify(eda.summary, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------ */}
      {/* TEXT 전용 뷰 */}
      {/* ------------------------------------------------------ */}
      {type === "text" && (
        <div className="space-y-4">
          <div className="bg-white rounded shadow p-3">
            <div className="font-semibold text-sm mb-2">Line Stats</div>
            <div className="text-xs mb-2">
              Total lines: {eda.num_lines}
              <br />
              Avg line length: {eda.avg_line_length?.toFixed(2)}
            </div>

            <div className="font-semibold text-sm mb-2">Preview</div>
            <pre className="text-xs whitespace-pre-wrap">
              {(eda.preview || []).join("\n")}
            </pre>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------ */}
      {/* ZIP 전용 뷰 (roboflow/yolo/coco/voc/bundles) */}
      {/* ------------------------------------------------------ */}
      {type === "zip" && (
        <div className="space-y-4">
          {/* Zip basic info */}
          <div className="bg-white rounded shadow p-3">
            <div className="font-semibold text-sm mb-2">
              ZIP Type
            </div>
            <div className="text-xs">{eda.zip_type}</div>
          </div>

          {/* Stats */}
          <div className="bg-white rounded shadow p-3">
            <div className="font-semibold text-sm mb-2">Stats</div>
            <pre className="text-xs">
              {JSON.stringify(eda.stats, null, 2)}
            </pre>
          </div>

          {/* Roboflow stats */}
          {eda.roboflow && (
            <div className="bg-white rounded shadow p-3">
              <div className="font-semibold text-sm mb-2">
                Roboflow EDA
              </div>

              <div className="text-xs mb-2">
                <div className="font-semibold">Classes</div>
                <div className="flex flex-wrap gap-1">
                  {eda.roboflow.classes.map((c) => (
                    <span
                      key={c}
                      className="px-2 py-1 bg-gray-100 border rounded text-gray-700"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                {Object.entries(eda.roboflow.splits).map(
                  ([splitName, s]) => (
                    <div key={splitName} className="mb-2">
                      <div className="font-semibold text-xs mb-1">
                        {splitName}
                      </div>
                      <div className="text-xs">
                        Images: {s.num_images}, Labels: {s.num_labels}
                      </div>

                      {s.class_counts && (
                        <div className="ml-2 text-[11px]">
                          {Object.entries(s.class_counts).map(
                            ([cls, cnt]) => (
                              <div key={cls}>
                                {cls}: {cnt}
                              </div>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  )
                )}
              </div>
            </div>
          )}

          {/* Tree view */}
          <div className="bg-white rounded shadow p-3">
            <div className="font-semibold text-sm mb-2">
              Directory Tree
            </div>

            <TreeView node={eda.tree} />
          </div>
        </div>
      )}

      {/* ------------------------------------------------------ */}
      {/* FALLBACK */}
      {/* ------------------------------------------------------ */}
      {!["csv", "text", "zip"].includes(type) && (
        <div className="bg-white rounded shadow p-3">
          <div className="font-semibold text-sm mb-2">EDA</div>
          <pre className="text-xs">
            {JSON.stringify(eda, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}



/* ---- ZIP 트리뷰 재귀 컴포넌트 ---- */
function TreeView({ node, depth = 0 }) {
  if (!node) return null;

  return (
    <div className="ml-2">
      <div className="text-xs flex items-center gap-1">
        {node.children ? "📁" : "📄"} {node.name}
      </div>
      {node.children &&
        node.children.map((c) => (
          <TreeView key={c.name + depth} node={c} depth={depth + 1} />
        ))}
    </div>
  );
}