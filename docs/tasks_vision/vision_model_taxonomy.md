# Vision Model Taxonomy

- JPark with GPT4o, July 2025

최신 컴퓨터 비전 기술은 다양한 연구 분야와 애플리케이션을 포함하고 있으며, 기술 발전의 흐름에 따라 다음과 같은 **텍소노미(Taxonomy)**로 분류할 수 있습니다. 각 분야별로 SOTA(State-of-the-Art) 기술도 함께 요약합니다.

⸻

## ✅ 컴퓨터 비전 기술의 텍소노미

### 1. 이미지 분류 (Image Classification)
	•	목표: 이미지 하나에 대해 하나 혹은 여러 개의 클래스 레이블 예측
	•	SOTA 모델:
	•	ConvNeXt V2 (2023): Conv 기반이지만 Transformer 수준 성능
	•	ViT (Vision Transformer): Transformer 구조로 이미지 분류 성능을 혁신
	•	Swin Transformer: 계층적 구조로 로컬-글로벌 정보 결합
	•	CoAtNet: CNN과 Attention의 장점 결합

⸻

### 2. 객체 탐지 (Object Detection)
	•	목표: 이미지 속 객체 위치(Bounding Box)와 클래스 예측
	•	SOTA 모델:
	•	YOLOv8 (Ultralytics): 실시간 처리에 최적화, 경량 모델
	•	DETR / DINO-DETR: Transformer 기반의 End-to-End 탐지
	•	RT-DETR (2023): Real-Time DETR, 속도·정확도 균형

⸻

### 3. 인스턴스 분할 (Instance Segmentation)
	•	목표: 각 객체의 픽셀 단위 마스크 추출
	•	SOTA 모델:
	•	Mask R-CNN: 대표적인 2단계 방식
	•	Segment Anything Model (SAM, Meta AI, 2023):
	•	범용 세그멘테이션 모델
	•	프롬프트 기반 인터랙션 지원
	•	Mask2Former: Unified Transformer 기반 segmentation

⸻

### 4. 시맨틱 분할 (Semantic Segmentation)
	•	목표: 이미지의 각 픽셀에 클래스 레이블 지정
	•	SOTA 모델:
	•	DeepLabV3+
	•	SegFormer (NVIDIA): Transformer 기반으로 경량화 및 정확도 개선
	•	HRNet: 고해상도 피처 맵 유지로 정확도 향상

⸻

### 5. Depth Estimation / 3D Vision
	•	목표: 단일 이미지나 스테레오 이미지에서 깊이 정보 추정
	•	SOTA 모델:
	•	MiDaS (Intel): 다양한 스케일의 입력에 강건
	•	DPT (Dense Prediction Transformer)
	•	NeRF (Neural Radiance Fields): 뷰포인트 기반 3D 재구성

⸻

### 6. Pose Estimation (자세 추정)
	•	목표: 사람 혹은 물체의 키포인트 위치 추정
	•	SOTA 모델:
	•	OpenPose
	•	HRNet
	•	DEKR (Differentiable Keypoint Regression)

⸻

### 7. 비디오 이해 (Video Understanding)
	•	목표: 비디오에서 객체 추적, 동작 인식 등
	•	SOTA 모델:
	•	SlowFast Networks: 빠른-느린 경로 병렬 처리
	•	TimeSFormer: Vision Transformer를 시간축까지 확장
	•	InternVideo (OpenCVLab, 2023)

⸻

### 8. 멀티모달 비전 (Multimodal Vision)
	•	목표: 이미지+텍스트, 이미지+음성 등 복합 정보 처리
	•	SOTA 모델:
	•	CLIP (OpenAI): 이미지-텍스트 임베딩 정렬
	•	BLIP-2: 비전-랭귀지 모델의 강화된 생성 능력
	•	Kosmos-2 / GPT-4o: 자연어와 시각 정보의 통합

⸻

### 9. 기초 모델 및 프리트레인 (Foundation Models in CV)
	•	SOTA:
	•	SAM (Segment Anything)
	•	DINOv2 (Meta)
	•	CLIP / OpenCLIP
	•	Grok-1.5 Vision (xAI, 2024)
	•	GPT-4o (OpenAI, 2024): 멀티모달 입력 통합

⸻

### 🔍 트렌드 요약

- Transformer의 비전 도입	: ViT, Swin, Mask2Former 등
- 멀티모달/프롬프트 기반	: SAM, CLIP, BLIP, GPT-4o
- 경량화와 실시간 처리	: YOLOv8, RT-DETR
- Self-supervised 학습	: DINO, MAE
- Foundation Models	: 범용 모델 등장, 적은 데이터로 다양한 작업 수행




## 대표 기술 

⸻

### ✅ 1. CLIP (Contrastive Language–Image Pretraining, OpenAI, 2021)
	•	파급효과:
	•	이미지와 텍스트를 동일한 임베딩 공간에 매핑함으로써, “텍스트 기반 이미지 검색”, 제로샷 분류, 멀티모달 프롬프트 학습 등을 가능하게 함
	•	멀티모달 비전 모델의 기반 인프라 역할 (예: DALL·E, Stable Diffusion, BLIP 등에서 사용)
	•	대표 응용 분야:
	•	제로샷 인퍼런스, 이미지-텍스트 검색, 멀티모달 생성

⸻

### ✅ 2. Segment Anything Model (SAM, Meta AI, 2023)
	•	파급효과:
	•	범용 세그멘테이션 모델의 등장으로, 다양한 도메인(의료, 로보틱스, 위성 등)에서 마스크 생성이 쉬워짐
	•	클릭/박스/텍스트 등 프롬프트 기반 인터페이스 도입 → CV 모델의 활용성을 획기적으로 확장
	•	대표 응용 분야:
	•	이미지 편집, 데이터 레이블링 자동화, 의료 영상 분석, 인터랙티브 비전

⸻

### ✅ 3. DINOv2 (Self-supervised Vision Foundation Model, Meta AI, 2023)
	•	파급효과:
	•	Self-supervised 방식으로도 강력한 표현 학습이 가능함을 증명
	•	분류, 분할, 재식별 등 다양한 다운스트림 작업에서 좋은 성능 → 범용 CV 백본으로 부상
	•	사전학습된 모델을 다양한 태스크에 재사용 → 학습 비용 및 데이터 의존도 절감
	•	대표 응용 분야:
	•	산업용 비전 시스템, 로보틱스, 의료 AI, 딥러닝 백본 교체

⸻

### 🏁 요약 비교

- 이 3가지는 단순히 성능을 넘어서 비전 AI 패러다임 자체를 변화시키는 모델들입니다.

```csv
모델,	핵심 아이디어,	파급효과 및 핵심
CLIP,	텍스트-이미지 공동 임베딩 학습,	멀티모달 제로샷 가능
SAM,	프롬프트 기반 범용 세그멘테이션,	범용성 + 인터랙션 확장
DINOv2,	Self-supervised 비전, 백본	범용성 + 적은 라벨로 SOTA
```
