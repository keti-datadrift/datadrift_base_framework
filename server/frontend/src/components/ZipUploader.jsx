import React, { useState, useRef, useCallback } from "react";
import JSZip from "jszip";

/**
 * YOLOv5 데이터셋 전용 드래그 앤 드롭 업로더
 * 
 * YOLOv5 데이터셋 구조:
 * - images/ 폴더 (또는 train/images, valid/images, test/images)
 * - labels/ 폴더 (또는 train/labels, valid/labels, test/labels)
 * - data.yaml (선택적)
 */
export default function ZipUploader({ backend, onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  // 드래그 이벤트 핸들러
  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      handleFileSelect(droppedFiles[0]);
    }
  }, []);

  // 파일 선택 핸들러
  const handleFileSelect = async (selectedFile) => {
    setError(null);
    setValidationResult(null);

    // ZIP 파일 확인
    if (!selectedFile.name.toLowerCase().endsWith(".zip")) {
      setError("ZIP 파일만 업로드할 수 있습니다.");
      return;
    }

    setFile(selectedFile);
    setIsValidating(true);

    try {
      const result = await validateYOLOv5Format(selectedFile);
      setValidationResult(result);
      
      if (!result.isValid) {
        setError(result.error);
      }
    } catch (err) {
      setError(`파일 검증 중 오류 발생: ${err.message}`);
    } finally {
      setIsValidating(false);
    }
  };

  // 불필요한 파일/폴더 필터링 헬퍼
  const isJunkPath = (path) => {
    const lowerPath = path.toLowerCase();
    // __MACOSX 폴더
    if (lowerPath.includes("__macosx")) return true;
    // .DS_Store 파일
    if (lowerPath.includes(".ds_store")) return true;
    // ._ 로 시작하는 macOS 리소스 포크 파일
    const fileName = path.split("/").pop();
    if (fileName.startsWith("._")) return true;
    // Thumbs.db (Windows)
    if (lowerPath.includes("thumbs.db")) return true;
    return false;
  };

  // YOLOv5 포맷 검증
  const validateYOLOv5Format = async (zipFile) => {
    const zip = new JSZip();
    const contents = await zip.loadAsync(zipFile);
    
    // 불필요한 파일 제외
    const files = Object.keys(contents.files).filter(path => !isJunkPath(path));
    const folders = new Set();
    
    // 폴더 구조 분석
    files.forEach((path) => {
      const parts = path.split("/");
      if (parts.length > 1) {
        // 첫 번째 레벨 폴더 (루트 폴더 이름 제외)
        const rootFolder = parts[0];
        const subFolder = parts.length > 2 ? parts[1] : parts[0];
        folders.add(subFolder.toLowerCase());
        
        // 두 번째 레벨도 체크 (train/images 같은 구조)
        if (parts.length > 2) {
          folders.add(`${parts[1].toLowerCase()}/${parts[2].toLowerCase()}`);
        }
      }
    });

    // YOLOv5 구조 확인
    const hasImages = folders.has("images") || 
                      folders.has("train/images") || 
                      folders.has("valid/images") ||
                      folders.has("test/images");
    
    const hasLabels = folders.has("labels") || 
                      folders.has("train/labels") || 
                      folders.has("valid/labels") ||
                      folders.has("test/labels");

    // 이미지 파일 수 카운트 (불필요한 파일 이미 필터링됨)
    const imageExtensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"];
    const labelExtensions = [".txt"];
    
    let imageCount = 0;
    let labelCount = 0;
    
    files.forEach((path) => {
      const ext = path.toLowerCase().slice(path.lastIndexOf("."));
      if (imageExtensions.includes(ext)) imageCount++;
      if (labelExtensions.includes(ext) && !path.includes("data.yaml") && !path.includes("classes.")) {
        labelCount++;
      }
    });

    // data.yaml 확인
    const hasDataYaml = files.some((f) => 
      f.toLowerCase().endsWith("data.yaml") || 
      f.toLowerCase().endsWith(".yaml")
    );

    // 검증 결과
    const issues = [];
    
    if (!hasImages) {
      issues.push("images/ 폴더가 없습니다.");
    }
    if (!hasLabels) {
      issues.push("labels/ 폴더가 없습니다.");
    }
    if (imageCount === 0) {
      issues.push("이미지 파일이 없습니다.");
    }
    if (labelCount === 0) {
      issues.push("라벨 파일(.txt)이 없습니다.");
    }

    const isValid = hasImages && hasLabels && imageCount > 0;

    return {
      isValid,
      error: issues.length > 0 ? issues.join(" ") : null,
      stats: {
        imageCount,
        labelCount,
        hasDataYaml,
        folders: Array.from(folders).slice(0, 10),
      },
    };
  };

  // 업로드 실행
  const handleUpload = async () => {
    if (!file || !validationResult?.isValid) return;

    setIsUploading(true);
    setError(null);

    try {
      const form = new FormData();
      form.append("file", file);

      const response = await fetch(`${backend}/datasets/upload`, {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        throw new Error("업로드 실패");
      }

      // 성공 시 초기화
      setFile(null);
      setValidationResult(null);
      onUploadComplete?.();
    } catch (err) {
      setError(`업로드 중 오류 발생: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // 취소
  const handleCancel = () => {
    setFile(null);
    setValidationResult(null);
    setError(null);
  };

  return (
    <div className="w-full">
      {/* 드래그 앤 드롭 영역 */}
      {!file && (
        <div
          className={`
            relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
            transition-all duration-200 ease-in-out
            ${isDragging
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
            }
          `}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => e.target.files[0] && handleFileSelect(e.target.files[0])}
          />
          
          <div className="flex flex-col items-center gap-3">
            <div className="text-4xl">📦</div>
            <div className="text-sm font-medium text-gray-700">
              {isDragging ? "파일을 놓으세요" : "ZIP 파일을 드래그하거나 클릭하여 선택"}
            </div>
            <div className="text-xs text-gray-500">
              YOLOv5 데이터셋 포맷만 지원됩니다
            </div>
            <div className="text-xs text-gray-400 mt-2">
              필수 구조: images/, labels/ 폴더
            </div>
          </div>
        </div>
      )}

      {/* 파일 선택됨 - 검증 중 */}
      {file && isValidating && (
        <div className="border rounded-lg p-6 bg-gray-50">
          <div className="flex items-center gap-3">
            <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
            <div className="text-sm text-gray-600">파일 검증 중...</div>
          </div>
        </div>
      )}

      {/* 파일 선택됨 - 검증 완료 */}
      {file && !isValidating && validationResult && (
        <div className={`border rounded-lg p-4 ${validationResult.isValid ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{validationResult.isValid ? "✅" : "❌"}</span>
              <div>
                <div className="font-medium text-sm">{file.name}</div>
                <div className="text-xs text-gray-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </div>
              </div>
            </div>
            <button
              onClick={handleCancel}
              className="text-gray-400 hover:text-gray-600 text-lg"
            >
              ✕
            </button>
          </div>

          {/* 검증 결과 상세 */}
          {validationResult.isValid ? (
            <div className="space-y-2">
              <div className="text-xs text-green-700 font-medium">
                ✓ YOLOv5 데이터셋 포맷 확인됨
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-white p-2 rounded">
                  <div className="text-gray-500">이미지</div>
                  <div className="font-semibold">{validationResult.stats.imageCount}개</div>
                </div>
                <div className="bg-white p-2 rounded">
                  <div className="text-gray-500">라벨</div>
                  <div className="font-semibold">{validationResult.stats.labelCount}개</div>
                </div>
                <div className="bg-white p-2 rounded">
                  <div className="text-gray-500">data.yaml</div>
                  <div className="font-semibold">{validationResult.stats.hasDataYaml ? "있음" : "없음"}</div>
                </div>
              </div>
              
              {/* 업로드 버튼 */}
              <button
                onClick={handleUpload}
                disabled={isUploading}
                className="w-full mt-3 px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:bg-gray-400 transition"
              >
                {isUploading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                    업로드 중...
                  </span>
                ) : (
                  "업로드"
                )}
              </button>
            </div>
          ) : (
            <div className="text-xs text-red-700">
              <div className="font-medium mb-1">포맷 검증 실패:</div>
              <div>{validationResult.error}</div>
              <div className="mt-2 text-gray-500">
                감지된 폴더: {validationResult.stats.folders.join(", ") || "없음"}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 에러 메시지 */}
      {error && !validationResult && (
        <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="text-sm text-red-700">{error}</div>
        </div>
      )}
    </div>
  );
}


