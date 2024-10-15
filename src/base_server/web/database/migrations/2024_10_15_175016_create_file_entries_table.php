<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateFileEntriesTable extends Migration
{
    public function up()
    {
        Schema::create('file_entries', function (Blueprint $table) {
            $table->id();
            $table->string('file_name');  // 파일 이름을 저장할 문자열
            $table->string('file_type');  // 파일 유형을 저장할 문자열
            $table->longText('file_content');  // 파일 내용을 저장할 텍스트 필드 (대용량 텍스트)
            $table->timestamps();  // created_at, updated_at 필드 추가
        });
    }

    public function down()
    {
        Schema::dropIfExists('file_entries');
    }
}