
import torch
from drift_detection_module import MNISTDataLoader, SimpleCNN, ModelTrainer, DriftDetector, XAIAnalyzer, DriftResolver

# --- 설정 ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 64
TEST_BATCH_SIZE = 1000
EPOCHS = 5 # MNIST 학습에 충분한 Epochs

# --- 1. 데이터 로드 및 모델 학습 ---
print("--- 1. 데이터 로드 및 모델 학습 ---")
data_loader = MNISTDataLoader(batch_size=BATCH_SIZE, test_batch_size=TEST_BATCH_SIZE)
train_loader, initial_test_loader = data_loader.get_initial_loaders()

model = SimpleCNN()
model_trainer = ModelTrainer(model, device=DEVICE)
model_trainer.train(train_loader, epochs=EPOCHS)

# XAI 분석을 위한 모델과 predict_proba 함수 얻기
xai_model, predict_proba_fn = model_trainer.get_model_and_predict_proba()

# --- 2. 데이터 드리프트 감지 ---
# 새로운 데이터 로더 생성 (드리프트 타입 변경 가능: 'feature' 또는 'concept')
new_data_loader_drifted = data_loader.get_new_data_loader(drift_type='feature') # 'feature' 드리프트 시뮬레이션

drift_detector = DriftDetector(
    model_trainer=model_trainer,
    initial_test_loader=initial_test_loader
)

drift_detected, drift_features, X_new_flat, y_new = drift_detector.detect_drift(new_data_loader_drifted)

if drift_detected:
    print("\n데이터 드리프트가 감지되었습니다. XAI 분석을 시작합니다.")
    
    # --- 3. XAI를 통한 드리프트 원인 분석 및 진단 ---
    xai_analyzer = XAIAnalyzer(
        model=xai_model,
        predict_proba_fn=predict_proba_fn,
        X_initial_flat=drift_detector.X_initial_flat,
        y_initial=drift_detector.y_initial,
        feature_names=drift_detector.feature_names
    )
    
    # SHAP 분석
    initial_shap_importance, new_shap_importance = xai_analyzer.analyze_shap(
        X_new_flat, num_samples_to_explain=100
    ) # SHAP 계산 샘플 수 제한

    # LIME 분석
    xai_analyzer.analyze_lime(X_new_flat, num_samples_to_explain=5) # LIME 계산 샘플 수 제한

    # --- 4. 드리프트 해결 제안 ---
    drift_resolver = DriftResolver()
    drift_resolver.propose_solution(
        drift_detected=drift_detected,
        drift_features=drift_features,
        initial_shap_importance=initial_shap_importance,
        new_shap_importance=new_shap_importance,
        X_initial_flat=drift_detector.X_initial_flat,
        X_new_flat=X_new_flat,
        feature_names=drift_detector.feature_names
    )
else:
    print("\n데이터 드리프트가 감지되지 않았습니다. 모델은 현재 정상적으로 작동하는 것으로 보입니다.")

print("\n--- 데이터 드리프트 대응 프로세스 완료 ---")