<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class TimeSeries extends Model
{
    use HasFactory;


    // 필요한 경우 테이블 이름을 지정할 수 있습니다.
    // protected $table = 'time_series';

    // 자동으로 'recorded_at'을 datetime 형식으로 변환
    protected $casts = [
        'recorded_at' => 'datetime',
    ];

    // 필드 보호 설정 (mass assignment)
    protected $fillable = ['recorded_at', 'value'];
}
