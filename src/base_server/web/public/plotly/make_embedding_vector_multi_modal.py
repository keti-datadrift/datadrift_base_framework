import numpy as np
import pandas as pd

# 가우시안 분포의 파라미터 설정 (평균과 공분산)
num_points = 10000  # 총 데이터 포인트 수

# 3개의 모달 각각의 평균
means = [
    [0, 0, 0],  # 첫 번째 모달의 평균
    [5, 5, 5],  # 두 번째 모달의 평균
    [-5, -5, -5]  # 세 번째 모달의 평균
]

# 각 모달의 공분산 행렬 (등방성 가우시안 분포: 공분산 행렬은 단위 행렬로 설정)
covariances = [
    np.identity(3),  # 첫 번째 모달의 공분산
    np.identity(3),  # 두 번째 모달의 공분산
    np.identity(3)   # 세 번째 모달의 공분산
]

# 각 모달에서 생성할 데이터 포인트 수
points_per_modal = num_points // 3

# 데이터 저장할 배열
x, y, z = [], [], []

# 각 모달에 대해 데이터를 생성
for mean, cov in zip(means, covariances):
    modal_data = np.random.multivariate_normal(mean, cov, points_per_modal)
    x.extend(modal_data[:, 0])
    y.extend(modal_data[:, 1])
    z.extend(modal_data[:, 2])

# 총 데이터 포인트가 1만 개를 넘을 경우 추가로 데이터 생성
if len(x) < num_points:
    remaining_points = num_points - len(x)
    additional_data = np.random.multivariate_normal(means[0], covariances[0], remaining_points)
    x.extend(additional_data[:, 0])
    y.extend(additional_data[:, 1])
    z.extend(additional_data[:, 2])

# DataFrame으로 변환
df = pd.DataFrame({'x': x, 'y': y, 'z': z})

# CSV 파일로 저장
df.to_csv('multimodal_embedding_vectors.csv', index=False)
