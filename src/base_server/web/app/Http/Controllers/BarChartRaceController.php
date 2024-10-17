<?php

namespace App\Http\Controllers;

use App\Models\CategoryValue;
use Illuminate\Http\Request;

class BarChartRaceController extends Controller
{
    public function index()
    {
        return view('bar_chart_race');
    }

    public function getData()
    {
        // 모든 데이터를 날짜 순으로 반환
        $data = CategoryValue::orderBy('date')->get();
        return response()->json($data);
    }
}