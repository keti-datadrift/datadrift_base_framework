import numpy as np
import pandas as pd

# 무작위로 1만 개의 3D 벡터 생성
num_points = 10000
x = np.random.randn(num_points)
y = np.random.randn(num_points)
z = np.random.randn(num_points)

# 데이터 프레임으로 변환
df = pd.DataFrame({'x': x, 'y': y, 'z': z})

# CSV 파일로 저장
df.to_csv('embedding_vectors.csv', index=False)
