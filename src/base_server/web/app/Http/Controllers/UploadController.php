<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use ZipArchive;
use File;
use Illuminate\Support\Facades\Storage;

class UploadController extends Controller
{
    public function upload(Request $request)
    {
        // 업로드된 파일 처리
        $request->validate([
            'compressed_file' => 'required|file|mimes:zip,rar,7z|max:102400', // 최대 100MB
        ]);

        $file = $request->file('compressed_file');
        $fileName = $file->getClientOriginalName();
        $filePath = $file->storeAs('uploads', $fileName);

        // 업로드 성공 후 파일 경로 및 기타 정보를 출력
        if ($filePath) {
            $fileInfo = $this->extractFiles(storage_path('app/' . $filePath));

            return response()->json([
                'message' => 'File uploaded successfully!',
                'uploaded_file' => $fileName,
                'file_path' => $filePath,
                'file_info' => $fileInfo,
            ]);
        }

        return response()->json(['message' => 'File upload failed.' + $fileName + ', ' + $filePath + ', ' + $fileInfo ], 500);
    }

    private function extractFiles($filePath)
    {
        $zip = new ZipArchive;
        $fileInfo = [];
        $fileTypes = [];
        $totalFiles = 0;

        if ($zip->open($filePath) === TRUE) {
            for ($i = 0; $i < $zip->numFiles; $i++) {
                $file = $zip->statIndex($i);
                $totalFiles++;

                // 파일 정보 추출
                $fileType = $this->getFileType($file['name']);
                $fileSize = $file['size'];

                // 파일 유형별 크기 계산
                if (!isset($fileTypes[$fileType])) {
                    $fileTypes[$fileType] = 0;
                }
                $fileTypes[$fileType] += $fileSize;
            }
            $zip->close();
        }

        // 각 파일 유형과 그 크기를 구조화하여 반환
        $fileInfo['total_files'] = $totalFiles;
        $fileInfo['file_types'] = array_map(function ($type, $size) {
            return ['type' => $type, 'size' => $size / 1024]; // KB로 변환
        }, array_keys($fileTypes), $fileTypes);

        return $fileInfo;
    }

    private function getFileType($fileName)
    {
        $extension = pathinfo($fileName, PATHINFO_EXTENSION);

        // 파일 유형 정의
        $imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp'];
        $textExtensions = ['txt', 'doc', 'docx', 'pdf'];
        $audioExtensions = ['mp3', 'wav', 'ogg'];
        $videoExtensions = ['mp4', 'avi', 'mkv'];

        if (in_array($extension, $imageExtensions)) {
            return 'Image';
        } elseif (in_array($extension, $textExtensions)) {
            return 'Text';
        } elseif (in_array($extension, $audioExtensions)) {
            return 'Audio';
        } elseif (in_array($extension, $videoExtensions)) {
            return 'Video';
        } else {
            return 'Other';
        }
    }
}