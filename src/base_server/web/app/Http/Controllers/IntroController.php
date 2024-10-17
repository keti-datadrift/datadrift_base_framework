<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class IntroController extends Controller
{
    public function showIntro()
    {
        return view('intro_controller');
    }
}