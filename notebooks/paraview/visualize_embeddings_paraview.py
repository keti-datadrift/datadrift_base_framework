# visualize_embeddings_from_csv_paraview.py
from paraview.simple import *
import os

# --- 설정 ---
CSV_FILE_PATH = './tmp/dinov2_embeddings.csv' # 파트 1에서 생성된 CSV 파일 경로
OUTPUT_IMAGE_FILE = './tmp/dinov2_embedding_visualization.png' # 저장될 이미지 파일 이름

# --- 1. ParaView 뷰 생성 ---
renderView = GetActiveViewOrCreate(viewtype='RenderView')
renderView.ResetCamera()

# 2. CSV 파일 로드
print(f"Loading CSV file: {CSV_FILE_PATH}...")
if not os.path.exists(CSV_FILE_PATH):
    print(f"Error: CSV file '{CSV_FILE_PATH}' not found. Please run 'generate_dinov2_embeddings_to_csv.py' first.")
    exit()

csv_reader = CSVReader(FileName=CSV_FILE_PATH)

# 3. CSV 데이터를 3D 포인트로 변환 (TableToPoints 필터 사용)
# X, Y, Z 컬럼을 명시적으로 지정합니다.
table_to_points = TableToPoints(Input=csv_reader)
table_to_points.XColumn = 'X'
table_to_points.YColumn = 'Y'
table_to_points.ZColumn = 'Z'
table_to_points.KeepAllDataArrays = 1 # 모든 추가 컬럼(Filename 포함)을 포인트 데이터로 유지

# 4. 데이터 표시
display = Show(table_to_points, renderView)

# 5. 시각화 설정
display.PointSize = 5 # 점의 크기 조절 (필요에 따라 조절)

# 예시: 'Filename' 컬럼은 문자열이므로 직접 색상 매핑이 안 됩니다.
# 만약 Label과 같은 숫자 속성이 있다면 ColorBy를 사용할 수 있습니다.
# ColorBy(display, ('POINTS', 'Label'))
# label_LUT = GetColorTransferFunction('Label')
# label_LUT.ApplyPreset('Cool to Warm', True)
# label_LUT.UseDiscreteColors = 1

# 6. 렌더링 및 저장
Render()
SaveScreenshot(OUTPUT_IMAGE_FILE, renderView, ImageResolution=[1200, 900])

print(f"DINOv2 embedding visualization saved to '{OUTPUT_IMAGE_FILE}'.")
print("ParaView script finished.")

# ParaView 연결 종료
Disconnect()