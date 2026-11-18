문제 재현 케이스까지 딱 집어주셔서 해결이 쉬웠습니다! 🙌
다음 내용을 반영해 services/dataset_manager.py를 전면 리팩토링해서 캔버스에 추가했습니다.

무엇이 달라졌나요?

1) PIL 오류 근본 해결
	•	**안전 이미지 검증(_is_valid_image)**을 추가해, 미리보기 전에 **Pillow Image.verify()**로 헤더만 빠르게 검사합니다.
	•	확장자만 보고 열지 않으며, 잘못 라벨된 파일/깨진 파일은 자동 스킵 → PIL.UnidentifiedImageError 방지.
	•	preview_samples()는 항상 유효한 이미지만 반환하므로 st.image([...])에서 예외가 나지 않습니다.
	•	디렉터리 스캔은 rglob('**/*') 기반이라 d3/images/*.jpg와 d3/d3/images/*.jpg 모두 처리합니다.

2) 포맷/모달리티 확장
	•	포맷 힌트 감지: YOLO, Pascal VOC, COCO, UNKNOWN
	•	YOLO: labels/*.txt + images/*
	•	VOC: Annotations/*.xml + JPEGImages/*
	•	COCO: annotations/*.json + images/*
	•	모달리티 카운트: 이미지, 텍스트, 오디오, 비디오, CSV(시계열), XML, JSON, 기타 + 총 용량(GB)
	•	확장 가능 설계: FileType, DatasetFormat, EXT 집합만 늘리면 새로운 유형 쉽게 지원

3) API 정리 (호환 유지 + 확장)
	•	업로드/추출/추적: save_uploaded_zip, extract_zip, track_and_commit_dataset, ensure_data_branch
	•	요약/탐색:
	•	summarize_dataset(ds_dir) → 숫자/용량 + 포맷 명칭
	•	preview_samples(ds_dir, limit=12) → 검증된 이미지 경로 리스트
	•	diff_stats(left_dict, right_dict) → 두 요약의 차이(숫자형 지표만 Δ)
	•	(옵션) YOLO 파서 스텁 제공: parse_yolo_label_line, count_yolo_labels

교체 방법
	•	캔버스의 services/dataset_manager.py 파일 내용을 프로젝트에 그대로 복사해 덮어쓰세요.
	•	views/tabs_data.py에서 이미지 미리보기는 다음처럼 바꾸면 안전합니다.

from services.dataset_manager import preview_samples
# ...
imgs = preview_samples(ds_dir, limit=12)
if imgs:
    st.image([str(p) for p in imgs], width='stretch')

(use_container_width 경고 대응으로 width='stretch' 사용)

추가 확장 아이디어
	•	오디오/비디오 길이/프레임레이트: ffprobe 있을 때만 메타데이터 가볍게 수집(옵션)
	•	YOLO/VOC/COCO 클래스 분포: 포맷 감지 시 클래스 통계 카드 표시
	•	CSV/시계열 샘플 플롯: 파일 크기 제한 두고 상위 N개 칼럼만 단순 라인차트 미리보기

원하시면 위 확장까지 바로 넣어 드릴게요.
다음으로 어떤 포맷(예: COCO annotations)까지 구체적으로 보강할까요?