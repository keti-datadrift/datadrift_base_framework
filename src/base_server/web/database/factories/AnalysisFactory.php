<?php

namespace Database\Factories;

use App\Models\Analysis;
use Illuminate\Database\Eloquent\Factories\Factory;

class AnalysisFactory extends Factory
{
    protected $model = Analysis::class;

    /**
     * Define the model's default state.
     *
     * @return array
     */
    public function definition()
    {
        return [
            'title' => $this->faker->sentence,
            'content' => json_encode($this->faker->randomElements([12, 19, 3, 5, 2, 3], 6)),
            'type' => $this->faker->randomElement(['text', 'chart']),
        ];
    }
}