import pickle

def run(model1, model2, output):
    with open(model1, "rb") as f1, open(model2, "rb") as f2:
        m1 = pickle.load(f1)
        m2 = pickle.load(f2)

    fused_model = (m1 + m2) / 2  # 단순 평균 (실제로는 더 복잡한 로직 적용 가능)

    with open(output, "wb") as f:
        pickle.dump(fused_model, f)

    print(f"✅ 모델 융합 완료: {output}")