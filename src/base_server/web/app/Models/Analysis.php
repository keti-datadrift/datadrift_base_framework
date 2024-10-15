<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Analysis extends Model
{
    use HasFactory;

    protected $table = 'analyses';

    // Mass assignment 허용
    protected $fillable = ['title', 'content', 'type'];
}