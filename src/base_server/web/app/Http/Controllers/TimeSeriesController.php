<?php

namespace App\Http\Controllers;

use App\Models\TimeSeries;
use Illuminate\Http\Request;

class TimeSeriesController extends Controller
{
    public function index()
    {
        // 최근 30일의 데이터 반환
        $data = TimeSeries::where('recorded_at', '>=', now()->subDays(30))
                          ->orderBy('recorded_at', 'asc')
                          ->get();
                          
        return response()->json($data);
    }
}