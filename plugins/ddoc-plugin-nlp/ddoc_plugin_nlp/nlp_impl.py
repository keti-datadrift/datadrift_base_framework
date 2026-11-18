import pluggy
from typing import Any, Dict, Optional
from pathlib import Path

# ddoc용 hookimpl 마커 정의
hookimpl = pluggy.HookimplMarker("ddoc")

class DDOCNlpPlugin:
    """텍스트 데이터에 대한 토큰화 및 정규화 변환을 제공합니다."""
    
    @hookimpl(tryfirst=True) # 변환 훅을 우선적으로 실행하도록 설정
    def transform_apply(self, input_path: str, transform: str, args: Dict[str, Any], output_path: str) -> Optional[Dict[str, Any]]:
        """
        NLP 변환: text.tokenize, text.normalize (예시 구현).
        """
        if transform not in {"text.tokenize", "text.normalize"}:
            return None  # 이 플러그인에서 처리하지 않는 변환은 None 반환 (다음 플러그인으로 처리가 넘어감)
    
        try:
            # 입력 파일을 읽습니다.
            text = Path(input_path).read_text(encoding="utf-8")
        except FileNotFoundError:
            return {"ok": False, "error": f"Input file not found: {input_path}", "provider": "ddoc_nlp"}

        result = None
        if transform == "text.tokenize":
            # 텍스트를 공백 기준으로 단순 토큰화 및 소문자 변환
            tokens = text.lower().replace('.', ' ').split()
            Path(output_path).write_text("\n".join(tokens), encoding="utf-8")
            result = {"ok": True, "written": output_path, "transform": transform, "provider": "ddoc_nlp", "summary": f"Generated {len(tokens)} tokens"}
        
        elif transform == "text.normalize":
            # 다중 공백 및 양쪽 끝 공백 제거
            norm = " ".join(text.split())
            Path(output_path).write_text(norm, encoding="utf-8")
            result = {"ok": True, "written": output_path, "transform": transform, "provider": "ddoc_nlp", "summary": "Text normalization complete"}
        
        return result

    @hookimpl
    def ddoc_get_metadata(self) -> Dict[str, Any]:
        """플러그인의 메타데이터를 제공하는 훅."""
        return {"name": "ddoc_nlp", "implemented": ["transform_apply", "todo_bhc"]}

    @hookimpl
    def ddoc_get_metadata2(self) -> Dict[str, Any]:
        """플러그인의 메타데이터를 제공하는 훅."""
        return {"name": "ddoc_nlp", "implemented": ["transform_apply2", "todo_bhc2"]}
        