import React, { useState } from "react";

export default function DatasetWorkspace({ datasets, onUploaded, onSelect, onCompare }) {
  const [file, setFile] = useState(null);

  const upload = () => {
    const form = new FormData();
    form.append("file", file);

    fetch("http://localhost:8000/datasets/upload", {
      method: "POST",
      body: form,
    }).then(() => {
      onUploaded();
      setFile(null);
    });
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">📁 Dataset Workspace</h2>

      {/* Upload */}
      <div className="p-4 bg-white shadow rounded-xl mb-6">
        <div className="flex gap-4">
          <input
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
            className="text-sm"
          />
          <button
            onClick={upload}
            disabled={!file}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg disabled:bg-gray-300"
          >
            Upload
          </button>
        </div>
      </div>

      {/* List */}
      <h3 className="text-xl font-semibold mb-3">📄 Uploaded Datasets</h3>

      <div className="space-y-3">
        {datasets.map((ds) => (
          <div
            key={ds.id}
            className="p-4 bg-white shadow rounded-lg border hover:border-blue-400 transition"
          >
            <div className="flex justify-between items-center">
              <div>
                <div className="font-bold text-lg">{ds.name}</div>
                <div className="text-sm text-gray-600">
                  {ds.rows} rows · {ds.cols} columns
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => onSelect(ds)}
                  className="px-3 py-2 bg-green-600 text-white rounded-md"
                >
                  View EDA
                </button>
                <button
                  onClick={() => onCompare(ds)}
                  className="px-3 py-2 bg-purple-600 text-white rounded-md"
                >
                  Compare Drift
                </button>
              </div>
            </div>
          </div>
        ))}

        {datasets.length === 0 && (
          <div className="text-gray-500">아직 데이터셋이 없습니다.</div>
        )}
      </div>
    </div>
  );
}