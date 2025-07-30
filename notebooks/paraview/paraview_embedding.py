# pvpython_embedding_example.py
from paraview.simple import *
import numpy as np
import os

# 가상의 임베딩 데이터 생성 (3D, 100개 점, 2개 클래스)
num_points = 100
np.random.seed(42)
embeddings = np.random.rand(num_points, 3) * 10 # 0~10 범위의 랜덤 3D 좌표
labels = np.random.randint(0, 2, num_points) # 0 또는 1 레이블

# 데이터를 CSV 파일로 저장
csv_filename = './tmp/embeddings_data.csv'
with open(csv_filename, 'w') as f:
    f.write('X,Y,Z,Label\n')
    for i in range(num_points):
        f.write(f'{embeddings[i,0]:.4f},{embeddings[i,1]:.4f},{embeddings[i,2]:.4f},{labels[i]}\n')

print(f"Embedding data saved to {csv_filename}")

# ParaView 시작
renderView = GetActiveViewOrCreate(viewtype='RenderView')
renderView.ResetCamera()

# CSV 파일 로드
csv_reader = CSVReader(FileName=csv_filename)

# TableToPoints 필터 적용
table_to_points = TableToPoints(Input=csv_reader)
table_to_points.XColumn = 'X'
table_to_points.YColumn = 'Y'
table_to_points.ZColumn = 'Z'
table_to_points.KeepAllDataArrays = 1 # 원본 CSV의 모든 컬럼 유지

# 데이터 표시
display = Show(table_to_points, renderView)

# 점의 크기 조절
display.PointSize = 10 # 점을 더 크게 표시

# 'Label' 컬럼을 사용하여 색상 매핑
# 'Lable'이 정수형이므로 Discretize Coloring을 사용하여 명확한 색상 구분
ColorBy(display, ('POINTS', 'Label'))
label_LUT = GetColorTransferFunction('Label')
label_LUT.EnableOpacityMapping = 0
label_LUT.RescaleTransferFunction(0.0, 1.0) # Label이 0 또는 1이므로 범위를 0~1로 설정
#label_LUT.UseDiscreteColors = 1 # 이산적인 색상 사용
label_LUT.InterpretValuesAsCategories = 1 # 값들을 카테고리로 해석
label_LUT.ApplyPreset('Cool to Warm', True) # 원하는 색상 프리셋 적용

# 컬러 바 표시 (옵션)
label_LUT_bar = GetScalarBar(label_LUT, renderView)
label_LUT_bar.Title = 'Class Label'
label_LUT_bar.ComponentTitle = ''

# 렌더링 및 저장
Render()
output_image_filename = './tmp/embedding_visualization.png'
SaveScreenshot(output_image_filename, renderView, ImageResolution=[800, 600])

print(f"Embedding visualization saved to {output_image_filename}")

# 생성된 CSV 파일 삭제 (선택 사항)
# os.remove(csv_filename)

Disconnect()