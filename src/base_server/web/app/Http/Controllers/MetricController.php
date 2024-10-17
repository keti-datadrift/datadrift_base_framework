<?php

namespace App\Http\Controllers;

use App\Models\Metric;
use Illuminate\Http\Request;

class MetricController extends Controller
{
    public function store(Request $request)
    {
        Metric::create([
            'metric_name' => $request->input('metric_name'),
            'value' => $request->input('value'),
        ]);

        return response()->json(['status' => 'Metric stored']);
    }
}