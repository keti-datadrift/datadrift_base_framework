<?php

/** @var \Laravel\Lumen\Routing\Router $router */

/*
|--------------------------------------------------------------------------
| Application Routes
|--------------------------------------------------------------------------
|
| Here is where you can register all of the routes for an application.
| It is a breeze. Simply tell Lumen the URIs it should respond to
| and give it the Closure to call when that URI is requested.
|
*/



// routes/web.php

/*
$router->get('/', function () use ($router) {
    return $router->app->version();
});

$router->get('/', function () use ($router) {
    return 'Hello, Lumen!';
});
*/

$router->get('/api/chart-data', 'ChartController@getData');
$router->get('/', function () {
    return view('chart');
});

$router->get('/api/greet/{name}', function ($name) {
    return response()->json(['message' => "[greet1] Hello, $name!"]);
});

// routes/web.php
$router->get('/api/greet2/{name}', 'ExampleController@greet');
