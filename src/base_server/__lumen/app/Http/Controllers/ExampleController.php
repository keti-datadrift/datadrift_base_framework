<?php

// app/Http/Controllers/ExampleController.php

namespace App\Http\Controllers;

use Laravel\Lumen\Routing\Controller as BaseController;

class ExampleController extends BaseController
{
    public function greet($name)
    {
        return response()->json(['message' => "[Controller] Hello, $name!"]);
    }
}