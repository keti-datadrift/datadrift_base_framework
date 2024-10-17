<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class FileEntry extends Model
{
    use HasFactory;

    // 대량 할당을 허용할 필드 정의
    protected $fillable = ['file_name', 'file_type', 'file_content'];

    // 추가적으로 필요한 모델 속성이나 관계 정의
}