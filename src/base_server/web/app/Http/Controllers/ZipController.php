<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;  // Log 클래스를 올바르게 가져옴
use App\Models\FileEntry;

class ZipController extends Controller
{
    public function index()
    {
        return view('upload');
    }
    
    public function upload(Request $request)
    {
        Log::info('[pass] start upload');

        /*
        if ($request->hasFile('zipfile')) {
            $file = $request->file('zipfile');
            dd([
                'original_name' => $file->getClientOriginalName(),
                'mime_type' => $file->getMimeType(),
                'size' => $file->getSize(),
            ]);
        } else {
            dd('[-] No file uploaded');
        }
        */

        // 유효성 검사
        /*
        $request->validate([
            'zipfile' => 'required|mimetypes:application/zip,application/octet-stream|max:51200',  // 최대 50MB 허용
        ]);
        */

        /*
        $request->validate([
    'zipfile' => 'required|mimetypes:application/zip,application/x-zip-compressed,application/octet-stream|max:51200',  // 최대 50MB 허용
]);
        */

        
        Log::info('[pass] validate');

        // 로그 확인
        if ($request->hasFile('zipfile')) {
            Log::info('[pass] hasFile ok');
            if ($request->file('zipfile')->isValid()) {
                Log::info('[dbg] File uploaded successfully: ' . $request->file('zipfile')->getClientOriginalName());
            } else {
                Log::error('[dbg] File upload failed.');
            }
        } else {
            Log::error('[dbg] No file uploaded');
        }

        // 업로드된 파일을 저장
        $file = $request->file('zipfile');
        $fileName = $file->getClientOriginalName();
        $filePath = $file->storeAs('uploads', $fileName);  // storage/app/uploads 디렉토리에 저장
        Log::info('[dbg] file: ' . $file);
        Log::info('[dbg] $fileName: ' . $fileName);
        Log::info('[dbg] $filePath: ' . $filePath);
        
        // 압축 파일을 저장할 디렉토리 경로
        $extractedPath = storage_path('app/extracted/' . pathinfo($fileName, PATHINFO_FILENAME));
        Log::info('[dbg] $extractedPath: ' . $extractedPath);

        // 압축 파일 해제: 서버에서 `unzip` 명령어 실행
        if (!is_dir($extractedPath)) {
            mkdir($extractedPath, 0755, true);
        }
        Log::info('[pass] mkdir ');

        // `unzip` 명령을 실행하여 ZIP 파일을 해제
        $unzipCommand = "unzip " . storage_path('app/' . $filePath) . " -d " . $extractedPath;
        $output = shell_exec($unzipCommand);
        Log::info('[pass] unzip ');

        // 해제된 파일 목록을 읽어 분석
        $files = scandir($extractedPath);
        $fileDetails = [];
        //Log::info('[dbg] $files: ' . $files);

        foreach ($files as $file) {
            // '.' 및 '..' 디렉토리와 숨김파일을 무시
            if ($file !== '.' && $file !== '..') {
                $filePath = $extractedPath . '/' . $file;
                
                // 디렉토리는 건너뛰고 파일만 처리
                if (!is_dir($filePath)) {
                    $fileType = pathinfo($filePath, PATHINFO_EXTENSION);
                    //$fileContent = file_get_contents($filePath);  // 파일 내용 읽기
                    $fileContent = 'todo';

                    /*
                    dd([
                        'file_name' => $file,
                        'file_type' => $fileType,
                        'file_content' => $fileContent,
                    ]);
                    */
    
                    
                    // 파일 정보 저장 (데이터베이스 또는 배열에)
                    FileEntry::create([
                        'file_name' => $file,
                        'file_type' => $fileType,
                        'file_content' => $fileContent,
                    ]);

                    $fileDetails[] = [
                        'file_name' => $file,
                        'file_type' => $fileType,
                        'file_size' => filesize($filePath),  // 파일 크기
                    ];
                }
            }
        }

        // 분석된 파일 정보를 뷰로 전달
        return view('result', ['fileDetails' => $fileDetails]);
    }
}