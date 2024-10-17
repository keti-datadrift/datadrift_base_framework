<?php

namespace Database\Seeders;

// use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class CategoryValueSeeder extends Seeder
{
    /**
     * Seed the application's database.
     */
    public function run()
    {
        $data = [
            ['date' => '2021-01-01', 'category' => 'A', 'value' => 100],
            ['date' => '2021-01-01', 'category' => 'B', 'value' => 90],
            ['date' => '2021-01-01', 'category' => 'C', 'value' => 80],
            ['date' => '2021-02-01', 'category' => 'A', 'value' => 120],
            ['date' => '2021-02-01', 'category' => 'B', 'value' => 100],
            ['date' => '2021-02-01', 'category' => 'C', 'value' => 95],
            ['date' => '2021-03-01', 'category' => 'A', 'value' => 150],
            ['date' => '2021-03-01', 'category' => 'B', 'value' => 110],
            ['date' => '2021-03-01', 'category' => 'C', 'value' => 85]
        ];
    
        foreach ($data as $item) {
            \App\Models\CategoryValue::create($item);
        }
    }
}
