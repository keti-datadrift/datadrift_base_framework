# convert_csv_to_vtp.py
from paraview.simple import *
import os

# --- 설정 ---
INPUT_CSV_FILE = './tmp/dinov2_embeddings.csv' # 입력 CSV 파일 경로 (파트 1에서 생성된 파일)
OUTPUT_VTP_FILE = './tmp/dinov2_embeddings_final.vtp' # 출력 VTP 파일 이름

# --- 1. CSV 파일 존재 여부 확인 ---
if not os.path.exists(INPUT_CSV_FILE):
    print(f"오류: 입력 CSV 파일 '{INPUT_CSV_FILE}'을 찾을 수 없습니다.")
    print("먼저 'generate_dinov2_embeddings_to_csv.py' 스크립트를 실행하여 CSV 파일을 생성해주세요.")
    exit()

print(f"CSV 파일 '{INPUT_CSV_FILE}'을 로드하여 VTP로 변환합니다.")

# --- 2. CSV 파일 로드 ---
csv_reader = CSVReader(FileName=INPUT_CSV_FILE)

# --- 3. CSV 데이터를 3D 포인트로 변환 (TableToPoints 필터 사용) ---
# X, Y, Z 컬럼을 명시적으로 지정합니다.
table_to_points = TableToPoints(Input=csv_reader)
table_to_points.XColumn = 'X'
table_to_points.YColumn = 'Y'
table_to_points.ZColumn = 'Z'
table_to_points.KeepAllDataArrays = 1 # CSV의 모든 추가 컬럼 (Filename 포함)을 포인트 데이터로 유지

# --- 4. 변환된 데이터를 VTP 파일로 저장 ---
# SaveData 함수를 사용하여 VTP (XML PolyData) 형식으로 저장합니다.
# writer = XMLPolyDataWriter(Input=table_to_points) # 명시적 Writer 사용도 가능하지만 SaveData가 더 간편합니다.
# writer.FileName = OUTPUT_VTP_FILE
# writer.UpdatePipeline()
SaveData(OUTPUT_VTP_FILE, proxy=table_to_points)

print(f"CSV 데이터가 '{OUTPUT_VTP_FILE}' 파일로 성공적으로 변환 및 저장되었습니다.")

# --- ParaView 연결 종료 ---
Disconnect()