<?php

namespace App\Http\Controllers;

use App\Models\Analysis;
use Illuminate\Http\Request;

class AnalysisController extends Controller
{
    public function dd_wolframstyle2()
    {
        // 모든 분석 데이터를 가져옵니다.
        $analyses = Analysis::all();
        return view('analyses.dd_wolframstyle2', compact('analyses'));
    }
    
    public function dd_wolframstyle3()
    {
        return view('analyses.dd_wolframstyle3');
    }

    public function dd_wolframstyle4()
    {
        return view('analyses.dd_wolframstyle4');
    }
    
    public function dd_wolframstyle5()
    {
        return view('analyses.dd_wolframstyle5');
    }
    
    public function search_wolframstyle5(Request $request)
    {
        // 키워드를 가져와 검색 수행
        $keyword = $request->input('keyword');
        $analyses = Analysis::where('title', 'LIKE', "%$keyword%")
                            ->orWhere('content', 'LIKE', "%$keyword%")
                            ->get();

        // 검색된 데이터를 뷰에 전달
        return view('analyses.dd_wolframstyle5', compact('analyses', 'keyword'));
    }

    
    // 탐색
    public function search(Request $request)
    {
        // 요청에서 키워드를 가져옵니다.
        $keyword = $request->input('keyword');

        // 키워드를 기반으로 데이터베이스에서 검색
        $analyses = Analysis::where('title', 'LIKE', "%$keyword%")
                            ->orWhere('content', 'LIKE', "%$keyword%")
                            ->get();

        // JSON 형식으로 반환합니다.
        return response()->json($analyses);
    }
}