import re
import numpy as np
from collections import Counter
#from langdetect import detect
#from sentence_transformers import SentenceTransformer, util
#from transformers import AutoTokenizer # AutoModel은 roberta-base를 인코더로 사용할 때 필요 없음

# 'base_analyzer' 모듈이 별도로 있다고 가정하고, import를 유지합니다.
from .base_analyzer import BaseAnalyzer 

# Define the model checkpoint name (KLUE RoBERTa-base)
model_checkpoint = "klue/roberta-base"

# --- Model & Tokenizer Initialization ---
# SentenceTransformer로 모델을 로드합니다. 이는 임베딩을 위한 최신 권장 방법입니다.
#model = SentenceTransformer(model_checkpoint)

# EDA의 문자열 토큰화를 위해 transformers의 AutoTokenizer를 명시적으로 로드합니다.
# model.tokenizer를 사용해도 되지만, 기존 코드 구조를 최대한 유지합니다.
#tokenizer = AutoTokenizer.from_pretrained(model_checkpoint) 

# ----------------------------------------

def tokenize(text):
    # 단어 단위 토큰화는 기존 정규표현식 방식 유지 (EDA 목적)
    return re.findall(r'\w+', text.lower())

class TextAnalyzer(BaseAnalyzer):
    def eda(self, file_path: str) -> dict:
        """텍스트 파일의 탐색적 데이터 분석(EDA)을 수행합니다."""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        # 기존 토큰화 방식 사용 (단어 개수, 빈도 계산 목적)
        tokens = [tokenize(line) for line in lines] 

        lengths = [len(t) for t in tokens]
        # 모든 단어를 하나의 리스트로 만듭니다.
        words = [w for line in tokens for w in line] 

        # 언어 감지 (첫 5줄 사용)
        lang = detect("\n".join(lines[:5])) if len(lines) >= 5 else "unknown"

        return {
            "num_lines": len(lines),
            "avg_words_per_line": float(np.mean(lengths)) if lengths else 0.0,
            "max_words_per_line": int(np.max(lengths)) if lengths else 0,
            "language": lang,
            "word_freq": Counter(words).most_common(20),
        }

    def drift(self, base_path: str, target_path: str) -> dict:
        """기준(base) 데이터셋과 대상(target) 데이터셋 간의 의미적 드리프트를 계산합니다."""
        
        def embed_lines(path):
            """파일을 읽어 라인별로 임베딩 벡터를 생성합니다."""
            with open(path, "r", encoding="utf-8") as f:
                # 드리프트 계산을 위해 텍스트 파일을 라인(문장) 단위로 임베딩합니다.
                lines = f.read().splitlines()
                # 빈 줄 제거
                lines = [line.strip() for line in lines if line.strip()] 
                # 메모리 효율을 위해 최대 200개 라인만 사용 (기존 코드 유지)
                lines_to_embed = lines[:200] 

            # SentenceTransformer 모델을 사용하여 임베딩합니다.
            # convert_to_tensor=True 설정으로 PyTorch 텐서를 반환받습니다.
            if not lines_to_embed:
                 return None
            #return model.encode(lines_to_embed, convert_to_tensor=True)
            return 'todo'

        base_emb = embed_lines(base_path)
        target_emb = embed_lines(target_path)
        
        # 데이터가 없는 경우 처리
        if base_emb is None or target_emb is None:
             return {
                "overall": 1.0, # 데이터가 없으면 최대 드리프트로 간주하거나 0으로 간주
                "method": "sentence-transformer cosine drift (empty data)",
             }

        # 두 임베딩 텐서 간의 코사인 유사도 행렬을 계산합니다.
        # util.cos_sim은 sentence_transformers 라이브러리에서 제공됩니다.
        cosine_matrix = util.cos_sim(base_emb, target_emb) 
        
        # 전체 평균 유사도를 계산하고, 드리프트 점수는 (1 - 평균 유사도)로 정의합니다.
        # 유사도가 낮을수록 (0에 가까울수록) 드리프트 점수(1에 가까움)가 높습니다.
        drift_score = 1 - float(cosine_matrix.mean()) 

        return {
            "overall": drift_score,
            "method": "sentence-transformer cosine drift",
        }