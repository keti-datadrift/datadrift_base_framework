#---------------------------------------------------------------
import pandas as pd
import umap
from sklearn.decomposition import PCA
import numpy as np

# CSV에서 임베딩 데이터를 로드
df = pd.read_csv("number-aug.csv")

# 첫 512개의 열이 임베딩 벡터라고 가정
embedding_vectors = df.iloc[:, :512].values
labels = df['label'].values  # 레이블

# UMAP으로 2D 변환
umap_model = umap.UMAP(n_components=2, random_state=42)
umap_projection = umap_model.fit_transform(embedding_vectors)

# PCA로 2D 변환
pca_model = PCA(n_components=2)
pca_projection = pca_model.fit_transform(embedding_vectors)

# 결과를 데이터프레임으로 변환
df_umap = pd.DataFrame(umap_projection, columns=['UMAP1', 'UMAP2'])
df_pca = pd.DataFrame(pca_projection, columns=['PCA1', 'PCA2'])

# 원래 레이블을 추가
df_umap['label'] = labels
df_pca['label'] = labels

# UMAP과 PCA 결과를 CSV로 저장
df_umap.to_csv("number-aug_umap_projection.csv", index=False)
df_pca.to_csv("number-aug_pca_projection.csv", index=False)

print("UMAP and PCA projections saved.")