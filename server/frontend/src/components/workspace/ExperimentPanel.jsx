import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";

/**
 * ExperimentPanel - Manage training experiments with extended parameters
 */
export default function ExperimentPanel({ workspaceId, workspaceApi, currentSnapshot }) {
  const [experiments, setExperiments] = useState([]);
  const [codeFiles, setCodeFiles] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [mlflowUrl, setMlflowUrl] = useState(null);
  const [loading, setLoading] = useState(true);

  // Run experiment form
  const [selectedScript, setSelectedScript] = useState("");
  const [expName, setExpName] = useState("");
  const [running, setRunning] = useState(false);
  
  // Extended experiment parameters
  const [expParams, setExpParams] = useState({
    // Basic training
    epochs: 10,
    batch: 16,
    
    // Learning rate
    learning_rate: 0.001,
    lr_scheduler: "cosine",
    warmup_epochs: 3,
    
    // Augmentation
    augmentation: true,
    mosaic: true,
    mixup: 0.15,
    
    // Saving
    save_best_only: true,
    early_stopping: 5,
    
    // Hardware
    device: "auto",
    workers: 8,
  });
  
  // Advanced params visibility
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Code upload
  const [uploading, setUploading] = useState(false);

  // Load data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      
      const [expRes, codeRes, templateRes, mlflowRes] = await Promise.all([
        axios.get(`${workspaceApi}/workspace/${workspaceId}/experiments`),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/code/files`),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/code/templates`),
        axios.get(`${workspaceApi}/workspace/${workspaceId}/mlflow/url`),
      ]);
      
      setExperiments(expRes.data.experiments || []);
      setCodeFiles(codeRes.data.files || []);
      setTemplates(templateRes.data || []);
      setMlflowUrl(mlflowRes.data.mlflow_ui_url);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, workspaceApi]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Upload code
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploading(true);
      await axios.post(
        `${workspaceApi}/workspace/${workspaceId}/code/upload`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      loadData();
    } catch (err) {
      console.error("Upload failed:", err);
      alert("코드 업로드 실패");
    } finally {
      setUploading(false);
    }
  };

  // Apply template
  const applyTemplate = async (template) => {
    try {
      // Create a file blob from template content
      const blob = new Blob([template.content], { type: "text/plain" });
      const formData = new FormData();
      formData.append("file", blob, template.filename);

      await axios.post(
        `${workspaceApi}/workspace/${workspaceId}/code/upload`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      loadData();
    } catch (err) {
      console.error("Template apply failed:", err);
      alert("템플릿 적용 실패");
    }
  };

  // Run experiment
  const runExperiment = async () => {
    if (!selectedScript) {
      alert("트레이너 스크립트를 선택해주세요");
      return;
    }
    if (!expName.trim()) {
      alert("실험 이름을 입력해주세요");
      return;
    }

    try {
      setRunning(true);
      
      await axios.post(`${workspaceApi}/workspace/${workspaceId}/experiment/run`, {
        name: expName,
        trainer_script: selectedScript,
        params: expParams,
      });

      setExpName("");
      loadData();
    } catch (err) {
      console.error("Experiment failed:", err);
      alert("실험 시작 실패");
    } finally {
      setRunning(false);
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
      <div className="grid grid-cols-2 gap-6">
        {/* Code management */}
        <div>
          <h3 className="font-semibold mb-4">📝 트레이너 코드</h3>

          {/* Upload */}
          <div className="mb-4">
            <input
              type="file"
              accept=".py"
              onChange={handleFileUpload}
              className="hidden"
              id="code-upload"
            />
            <label
              htmlFor="code-upload"
              className="inline-block px-4 py-2 bg-gray-100 border rounded cursor-pointer hover:bg-gray-200"
            >
              {uploading ? "업로드 중..." : "📄 코드 파일 업로드"}
            </label>
          </div>

          {/* Code files */}
          {codeFiles.length > 0 ? (
            <div className="space-y-2 mb-4">
              {codeFiles.map((file) => (
                <div
                  key={file.filename}
                  className={`p-3 border rounded cursor-pointer transition ${
                    selectedScript === file.filename
                      ? "border-blue-500 bg-blue-50"
                      : "hover:border-gray-300"
                  }`}
                  onClick={() => setSelectedScript(file.filename)}
                >
                  <div className="font-medium">{file.filename}</div>
                  <div className="text-xs text-gray-500">
                    {(file.size_bytes / 1024).toFixed(1)} KB
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 bg-gray-50 rounded text-center text-gray-500 text-sm mb-4">
              업로드된 코드가 없습니다
            </div>
          )}

          {/* Templates */}
          <div>
            <div className="text-sm font-medium mb-2">템플릿</div>
            <div className="space-y-2">
              {templates.map((tmpl) => (
                <div
                  key={tmpl.name}
                  className="p-3 border rounded flex items-center justify-between"
                >
                  <div>
                    <div className="text-sm font-medium">{tmpl.name}</div>
                    <div className="text-xs text-gray-500">{tmpl.description}</div>
                  </div>
                  <button
                    onClick={() => applyTemplate(tmpl)}
                    className="text-xs text-blue-500 hover:underline"
                  >
                    적용
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Experiment execution */}
        <div>
          <h3 className="font-semibold mb-4">🚀 실험 실행</h3>
          
          {/* Current snapshot context */}
          <div className="mb-4 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
            📍 현재 스냅샷: <strong>{currentSnapshot || "초기 상태"}</strong>
            <span className="ml-2 text-blue-500">
              (실험은 이 데이터 버전에서 실행됩니다)
            </span>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">실험 이름</label>
              <input
                type="text"
                value={expName}
                onChange={(e) => setExpName(e.target.value)}
                placeholder="예: baseline_v1"
                className="w-full px-3 py-2 border rounded"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">트레이너 스크립트</label>
              <select
                value={selectedScript}
                onChange={(e) => setSelectedScript(e.target.value)}
                className="w-full px-3 py-2 border rounded"
              >
                <option value="">선택...</option>
                {codeFiles.map((file) => (
                  <option key={file.filename} value={file.filename}>
                    {file.filename}
                  </option>
                ))}
              </select>
            </div>

            {/* Basic Parameters */}
            <div className="p-3 bg-gray-50 rounded">
              <div className="text-sm font-medium mb-2">📊 기본 설정</div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-xs text-gray-500">Epochs</label>
                  <input
                    type="number"
                    value={expParams.epochs}
                    onChange={(e) => setExpParams({ ...expParams, epochs: parseInt(e.target.value) || 10 })}
                    className="w-full px-2 py-1 border rounded text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Batch Size</label>
                  <input
                    type="number"
                    value={expParams.batch}
                    onChange={(e) => setExpParams({ ...expParams, batch: parseInt(e.target.value) || 16 })}
                    className="w-full px-2 py-1 border rounded text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Learning Rate</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={expParams.learning_rate}
                    onChange={(e) => setExpParams({ ...expParams, learning_rate: parseFloat(e.target.value) || 0.001 })}
                    className="w-full px-2 py-1 border rounded text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Advanced Parameters Toggle */}
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full text-left text-sm text-gray-600 hover:text-gray-800 flex items-center gap-2"
            >
              <span>{showAdvanced ? "▼" : "▶"}</span>
              <span>고급 설정</span>
            </button>

            {/* Advanced Parameters */}
            {showAdvanced && (
              <div className="space-y-3">
                {/* Learning Rate Scheduler */}
                <div className="p-3 bg-gray-50 rounded">
                  <div className="text-sm font-medium mb-2">🔄 학습률 스케줄러</div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-gray-500">스케줄러</label>
                      <select
                        value={expParams.lr_scheduler}
                        onChange={(e) => setExpParams({ ...expParams, lr_scheduler: e.target.value })}
                        className="w-full px-2 py-1 border rounded text-sm"
                      >
                        <option value="cosine">Cosine</option>
                        <option value="step">Step</option>
                        <option value="linear">Linear</option>
                        <option value="none">None</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gray-500">Warmup Epochs</label>
                      <input
                        type="number"
                        value={expParams.warmup_epochs}
                        onChange={(e) => setExpParams({ ...expParams, warmup_epochs: parseInt(e.target.value) || 0 })}
                        className="w-full px-2 py-1 border rounded text-sm"
                      />
                    </div>
                  </div>
                </div>

                {/* Augmentation */}
                <div className="p-3 bg-gray-50 rounded">
                  <div className="text-sm font-medium mb-2">🎨 데이터 증강</div>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={expParams.augmentation}
                        onChange={(e) => setExpParams({ ...expParams, augmentation: e.target.checked })}
                        className="rounded"
                      />
                      증강 활성화
                    </label>
                    {expParams.augmentation && (
                      <div className="grid grid-cols-2 gap-2 pl-4">
                        <label className="flex items-center gap-2 text-xs">
                          <input
                            type="checkbox"
                            checked={expParams.mosaic}
                            onChange={(e) => setExpParams({ ...expParams, mosaic: e.target.checked })}
                            className="rounded"
                          />
                          Mosaic
                        </label>
                        <div>
                          <label className="text-xs text-gray-500">Mixup</label>
                          <input
                            type="number"
                            step="0.05"
                            min="0"
                            max="1"
                            value={expParams.mixup}
                            onChange={(e) => setExpParams({ ...expParams, mixup: parseFloat(e.target.value) || 0 })}
                            className="w-full px-2 py-1 border rounded text-sm"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Saving & Early Stop */}
                <div className="p-3 bg-gray-50 rounded">
                  <div className="text-sm font-medium mb-2">💾 저장 설정</div>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={expParams.save_best_only}
                        onChange={(e) => setExpParams({ ...expParams, save_best_only: e.target.checked })}
                        className="rounded"
                      />
                      Best 모델만 저장
                    </label>
                    <div>
                      <label className="text-xs text-gray-500">Early Stopping (epochs, 0=비활성)</label>
                      <input
                        type="number"
                        min="0"
                        value={expParams.early_stopping}
                        onChange={(e) => setExpParams({ ...expParams, early_stopping: parseInt(e.target.value) || 0 })}
                        className="w-full px-2 py-1 border rounded text-sm"
                      />
                    </div>
                  </div>
                </div>

                {/* Hardware */}
                <div className="p-3 bg-gray-50 rounded">
                  <div className="text-sm font-medium mb-2">🖥️ 하드웨어</div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-gray-500">Device</label>
                      <select
                        value={expParams.device}
                        onChange={(e) => setExpParams({ ...expParams, device: e.target.value })}
                        className="w-full px-2 py-1 border rounded text-sm"
                      >
                        <option value="auto">Auto</option>
                        <option value="cuda:0">CUDA:0</option>
                        <option value="cuda:1">CUDA:1</option>
                        <option value="cpu">CPU</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gray-500">Workers</label>
                      <input
                        type="number"
                        min="0"
                        max="32"
                        value={expParams.workers}
                        onChange={(e) => setExpParams({ ...expParams, workers: parseInt(e.target.value) || 0 })}
                        className="w-full px-2 py-1 border rounded text-sm"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            <button
              onClick={runExperiment}
              disabled={running || !selectedScript}
              className="w-full px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
            >
              {running ? "실행 중..." : "실험 시작"}
            </button>
          </div>

          {/* MLflow link */}
          {mlflowUrl && (
            <div className="mt-4 p-3 bg-purple-50 rounded">
              <a
                href={mlflowUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-purple-600 hover:underline flex items-center gap-2"
              >
                <span>📊</span>
                <span>MLflow 대시보드 열기</span>
              </a>
            </div>
          )}
        </div>
      </div>

      {/* Experiment history */}
      <div className="mt-6">
        <h3 className="font-semibold mb-4">📜 실험 기록</h3>
        {experiments.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left">이름</th>
                  <th className="px-4 py-2 text-left">상태</th>
                  <th className="px-4 py-2 text-left">데이터 버전</th>
                  <th className="px-4 py-2 text-left">생성 시간</th>
                  <th className="px-4 py-2 text-left">액션</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((exp) => (
                  <tr key={exp.experiment_id} className="border-t">
                    <td className="px-4 py-2 font-medium">{exp.name}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          exp.status === "completed"
                            ? "bg-green-100 text-green-700"
                            : exp.status === "running"
                            ? "bg-blue-100 text-blue-700"
                            : exp.status === "failed"
                            ? "bg-red-100 text-red-700"
                            : "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {exp.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-500">{exp.dataset_version}</td>
                    <td className="px-4 py-2 text-gray-500">
                      {new Date(exp.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2">
                      <button className="text-blue-500 hover:underline text-xs">
                        상세
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 bg-gray-50 rounded text-center text-gray-500">
            실험 기록이 없습니다
          </div>
        )}
      </div>
    </div>
  );
}
