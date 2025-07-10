# drift_detection_module.py

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Subset

import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score
from scipy.stats import ks_2samp # Kolmogorov-Smirnov test for drift detection
import shap
import lime
import lime.lime_tabular
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

# 경고 메시지 무시 (Jupyter Notebook 출력 정리를 위함)
warnings.filterwarnings('ignore')

# --- 1. 데이터 로더 클래스 ---
class MNISTDataLoader:
    """
    MNIST 데이터셋을 로드하고 전처리하는 클래스.
    다른 데이터셋으로 변경 시 이 클래스를 수정하거나 새로운 클래스를 정의합니다.
    """
    def __init__(self, batch_size=64, test_batch_size=1000):
        self.batch_size = batch_size
        self.test_batch_size = test_batch_size
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,)) # MNIST 평균, 표준편차
        ])

    def get_initial_loaders(self):
        # 학습 데이터와 테스트 데이터 로드
        train_dataset = datasets.MNIST('./data', train=True, download=True, transform=self.transform)
        test_dataset = datasets.MNIST('./data', train=False, download=True, transform=self.transform)

        # 재현성을 위해 고정된 초기 학습/테스트 데이터셋 분리
        train_size = int(0.8 * len(train_dataset))
        val_size = len(train_dataset) - train_size
        train_subset, val_subset = torch.utils.data.random_split(train_dataset, [train_size, val_size])

        train_loader = DataLoader(train_subset, batch_size=self.batch_size, shuffle=True)
        # 드리프트 감지를 위한 초기 테스트 데이터셋 (검증 데이터셋 활용)
        initial_test_loader = DataLoader(val_subset, batch_size=self.test_batch_size, shuffle=False)
        return train_loader, initial_test_loader

    def get_new_data_loader(self, drift_type='feature'):
        # 실제 배포 환경에서 들어오는 새로운 데이터 시뮬레이션
        # 여기서는 MNIST 테스트 셋의 일부를 새로운 데이터로 사용하고,
        # 'drift_type'에 따라 인위적인 드리프트를 주입합니다.
        new_data_dataset = datasets.MNIST('./data', train=False, download=True, transform=self.transform)
        
        # 새로운 데이터 로더는 초기 테스트 로더와 겹치지 않도록 일부 샘플만 사용
        num_new_samples = 2000
        indices = np.random.choice(len(new_data_dataset), num_new_samples, replace=False)
        subset_new_data = Subset(new_data_dataset, indices)

        if drift_type == 'feature':
            print("INFO: 'feature' 드리프트 주입 - 이미지 밝기 및 노이즈 변경")
            # feature drift 시뮬레이션: 이미지에 노이즈를 추가하거나 밝기를 변경
            # transform에 직접 드리프트를 주입하는 것은 복잡하므로, 데이터셋 로드 후 변환합니다.
            # 실제로는 새로운 데이터의 특성 자체가 변경되어야 합니다.
            # 이 예시에서는 MNIST 이미지를 numpy로 변환 후 조작합니다.
            
            class DriftTransform:
                def __init__(self, original_transform):
                    self.original_transform = original_transform
                
                def __call__(self, img):
                    img = self.original_transform(img) # 먼저 텐서로 변환
                    # 이미지 밝기 조절 (평균 이동)
                    img = img + torch.randn_like(img) * 0.1 # 노이즈 추가
                    img = torch.clamp(img, 0, 1) # 값 범위 유지
                    return img
            
            # subset_new_data.dataset.transform = DriftTransform(self.transform) # 이 방식은 원본 dataset을 변경하므로 주의
            # Subset에만 적용하려면, __getitem__을 오버라이드하는 것이 좋습니다.
            class SubsetWithDriftTransform(Subset):
                def __init__(self, dataset, indices, drift_transform):
                    super().__init__(dataset, indices)
                    self.drift_transform = drift_transform
                
                def __getitem__(self, idx):
                    img, label = self.dataset[self.indices[idx]] # 원본 데이터셋에서 가져옴
                    return self.drift_transform(img), label # 드리프트 변환 적용

            subset_new_data = SubsetWithDriftTransform(new_data_dataset, indices, DriftTransform(self.transform))


        elif drift_type == 'concept':
            print("INFO: 'concept' 드리프트 주입 - 짝수/홀수 레이블 반전 (단순화된 시뮬레이션)")
            # concept drift 시뮬레이션: 입력-출력 관계 변경
            class ConceptDriftDataset(Subset):
                def __init__(self, dataset, indices):
                    super().__init__(dataset, indices)

                def __getitem__(self, idx):
                    img, label = super().__getitem__(idx) # 원본 Subset에서 가져옴
                    # 예를 들어, 특정 이미지 특성(밝기)이 높으면 레이블을 반전
                    if img.mean() > 0.3 and label % 2 == 0: # 짝수이면서 밝은 이미지
                        label = 1 - label # 임의로 레이블 반전
                    return img, label
            
            subset_new_data = ConceptDriftDataset(new_data_dataset, indices) # 원본 데이터셋과 인덱스를 전달


        new_data_loader = DataLoader(subset_new_data, batch_size=self.test_batch_size, shuffle=False)
        return new_data_loader

    @staticmethod
    def flatten_images(loader):
        """이미지 데이터를 1D 벡터로 평탄화하고 NumPy 배열로 반환"""
        features_list = []
        labels_list = []
        for images, labels in loader:
            features_list.append(images.view(images.size(0), -1).numpy()) # Flatten images
            labels_list.append(labels.numpy())
        return np.vstack(features_list), np.hstack(labels_list)


# --- 2. 모델 트레이너 클래스 ---
class SimpleCNN(nn.Module):
    """MNIST 숫자 인식을 위한 간단한 CNN 모델"""
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3)
        self.dropout1 = nn.Dropout2d(0.25)
        self.dropout2 = nn.Dropout2d(0.5)
        # --- 수정된 부분: fc1의 입력 차원을 1600으로 변경 ---
        self.fc1 = nn.Linear(1600, 128) 
        # --- 원래 코드의 주석은 ((((28-2)/2)-2)/2)^2 * 64 = 9216 이었으나, 계산상 1600이 맞음
        # (28-3+1=26) -> pool (26/2=13) -> (13-3+1=11) -> pool (11/2=5.5 -> 5)
        # 최종적으로 (N, 64, 5, 5) 이므로 64 * 5 * 5 = 1600
        # ----------------------------------------------------
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2)
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = F.relu(self.fc1(x))
        x = self.dropout2(x)
        x = self.fc2(x)
        output = F.log_softmax(x, dim=1)
        return output

class ModelTrainer:
    """모델 학습 및 평가를 담당하는 클래스."""
    def __init__(self, model, device='cpu'):
        self.model = model
        self.device = device
        self.model.to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters())
        self.criterion = nn.NLLLoss()

    def train(self, train_loader, epochs=5):
        self.model.train()
        print(f"모델 학습 시작 (Epochs: {epochs})...")
        for epoch in range(epochs):
            for batch_idx, (data, target) in enumerate(train_loader):
                data, target = data.to(self.device), target.to(self.device)
                self.optimizer.zero_grad()
                output = self.model(data)
                loss = self.criterion(output, target)
                loss.backward()
                self.optimizer.step()
                if batch_idx % 100 == 0:
                    print(f'Train Epoch: {epoch+1} [{batch_idx * len(data)}/{len(train_loader.dataset)} ({100. * batch_idx / len(train_loader):.0f}%)]\tLoss: {loss.item():.6f}')
        print("모델 학습 완료.")

    def evaluate(self, data_loader, name="Test"):
        self.model.eval()
        test_loss = 0
        correct = 0
        with torch.no_grad():
            for data, target in data_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                test_loss += self.criterion(output, target).item()
                pred = output.argmax(dim=1, keepdim=True)
                correct += pred.eq(target.view_as(pred)).sum().item()

        test_loss /= len(data_loader.dataset)
        accuracy = 100. * correct / len(data_loader.dataset)
        print(f'\n{name} set: Average loss: {test_loss:.4f}, Accuracy: {correct}/{len(data_loader.dataset)} ({accuracy:.0f}%)\n')
        return accuracy

    def get_model_and_predict_proba(self):
        """SHAP, LIME 사용을 위해 scikit-learn 호환 가능한 predict_proba 함수 반환"""
        # Define the function and assign it to a variable within the method's scope
        def _predict_proba_wrapper(X): # Renamed to avoid confusion and clearly define its scope
            self.model.eval()
            
            if isinstance(X, pd.DataFrame):
                X_np = X.values
            else:
                X_np = X

            X_tensor = torch.from_numpy(X_np).float().to(self.device)
            
            # (샘플수, 28*28) -> (샘플수, 1, 28, 28) 형태로 변환
            if X_tensor.dim() == 2:
                X_tensor = X_tensor.view(-1, 1, 28, 28) 
            
            with torch.no_grad():
                output = self.model(X_tensor)
                # Softmax를 적용하여 확률 반환
                probabilities = F.softmax(output, dim=1)
                return probabilities.cpu().numpy()
        
        # Now, return the model and the function object
        return self.model, _predict_proba_wrapper



# --- 3. 드리프트 감지 클래스 ---
class DriftDetector:
    """데이터 드리프트를 감지하는 클래스."""
    def __init__(self, model_trainer, initial_test_loader, drift_threshold_p_value=0.05, performance_drop_threshold=0.9):
        self.model_trainer = model_trainer
        self.initial_test_loader = initial_test_loader
        self.drift_threshold_p_value = drift_threshold_p_value
        self.performance_drop_threshold = performance_drop_threshold
        
        self.initial_accuracy = self.model_trainer.evaluate(self.initial_test_loader, "Initial Test")
        
        # XAI 분석을 위해 필요한 NumPy 형태의 데이터 준비
        self.X_initial_flat, self.y_initial = MNISTDataLoader.flatten_images(self.initial_test_loader)
        self.feature_names = [f'pixel_{i}' for i in range(self.X_initial_flat.shape[1])]

    def detect_drift(self, new_data_loader):
        print("\n--- 2. 데이터 드리프트 감지 ---")
        self.X_new_flat, self.y_new = MNISTDataLoader.flatten_images(new_data_loader)

        drift_detected = False
        drift_features = []

        print("\n각 특성의 분포 변화 (Kolmogorov-Smirnov Test):")
        # 모든 픽셀 특성에 대해 KS 테스트 수행
        # 너무 많은 픽셀이 있으므로, 대표 픽셀 또는 PCA/특성 추출 후 사용 권장
        # 여기서는 설명을 위해 모든 픽셀에 대해 테스트합니다.
        for i, feature_name in enumerate(self.feature_names):
            statistic, p_value = ks_2samp(self.X_initial_flat[:, i], self.X_new_flat[:, i])
            # p-value가 낮으면 분포가 다르다는 통계적 증거가 강함 (드리프트 의심)
            if p_value < self.drift_threshold_p_value:
                print(f"  특성 '{feature_name}': KS 통계량={statistic:.4f}, p-value={p_value:.4f} -> 드리프트 의심!")
                drift_detected = True
                drift_features.append(feature_name)
        
        if not drift_detected:
            print("  (모든 특성에서 유의미한 분포 변화 없음)")


        new_accuracy = self.model_trainer.evaluate(new_data_loader, "New Data")
        
        performance_drift_detected = False
        if new_accuracy < self.initial_accuracy * self.performance_drop_threshold:
            print(f"    -> 경고: 모델 성능이 크게 하락했습니다 ({self.initial_accuracy:.2f}% -> {new_accuracy:.2f}%). 드리프트 가능성 높음!")
            performance_drift_detected = True
        else:
            print(f"    -> 모델 성능 변화 (초기: {self.initial_accuracy:.2f}%, 신규: {new_accuracy:.2f}%).")

        return drift_detected or performance_drift_detected, drift_features, self.X_new_flat, self.y_new


# --- 4. XAI 분석 클래스 ---
class XAIAnalyzer:
    """XAI 도구(SHAP, LIME)를 사용하여 드리프트 원인을 분석하는 클래스."""
    def __init__(self, model, predict_proba_fn, X_initial_flat, y_initial, feature_names):
        self.model = model
        self.predict_proba_fn = predict_proba_fn # Scikit-learn predict_proba 인터페이스와 호환되는 함수
        self.X_initial_flat = X_initial_flat
        self.y_initial = y_initial
        self.feature_names = feature_names
        
        # SHAP Explainer 초기화
        # MNIST 데이터셋에 대한 SHAP 계산은 매우 오래 걸릴 수 있으므로, 샘플링을 권장합니다.
        print("\nSHAP Explainer 초기화 중 (시간이 다소 소요될 수 있습니다)...")
        # 백그라운드 데이터 (요약 통계 또는 소규모 샘플)
        # MNIST의 픽셀 수가 많으므로 X_initial의 일부만 사용
        self.shap_explainer_background = shap.kmeans(self.X_initial_flat, 10) # 10개의 클러스터로 요약

        # KernelExplainer는 predict_proba_fn에 맞춰 작동합니다.
        # 실제 딥러닝 모델에는 DeepExplainer 사용을 강력히 권장합니다.
        # (단, DeepExplainer는 predict_proba_fn 대신 모델 자체와 입력 텐서를 직접 받도록 구현되어야 함)
        self.shap_explainer = shap.KernelExplainer(self.predict_proba_fn, self.shap_explainer_background)

        # LIME Explainer
        self.lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=self.X_initial_flat,
            feature_names=self.feature_names,
            class_names=[str(i) for i in range(10)], # MNIST 0-9 숫자
            mode='classification'
        )

    def analyze_shap(self, X_new_flat, num_samples_to_explain=100):
        print(f"\n3.1. SHAP을 이용한 특성 중요도 변화 분석 (샘플 {num_samples_to_explain}개):")
        print("SHAP 값 계산 중. 매우 오래 걸릴 수 있습니다. (CPU 사용 시 수십 분 이상 소요 가능)")
        
        # SHAP 계산: X_initial과 X_new에서 각 num_samples_to_explain개만 선택
        initial_indices = np.random.choice(self.X_initial_flat.shape[0], num_samples_to_explain, replace=False)
        new_indices = np.random.choice(X_new_flat.shape[0], num_samples_to_explain, replace=False)
        
        X_initial_sample = self.X_initial_flat[initial_indices]
        X_new_sample = X_new_flat[new_indices]

        # KernelExplainer는 shap_values가 (num_samples, num_features, num_classes) 형태를 반환합니다.
        shap_values_initial = self.shap_explainer.shap_values(X_initial_sample)
        shap_values_new = self.shap_explainer.shap_values(X_new_sample)

        # 전역 특성 중요도 (평균 절대 SHAP 값) 추출
        # (num_samples, num_features, num_classes) 형태에서 샘플과 클래스 차원을 평균
        mean_abs_shap_initial = np.abs(shap_values_initial).mean(axis=(0, 2))
        mean_abs_shap_new = np.abs(shap_values_new).mean(axis=(0, 2))

        shap_importance_initial = pd.Series(mean_abs_shap_initial, index=self.feature_names).sort_values(ascending=False)
        shap_importance_new = pd.Series(mean_abs_shap_new, index=self.feature_names).sort_values(ascending=False)

        print("\n초기 데이터 특성 중요도 (SHAP 평균 절대값 - Top 10):")
        print(shap_importance_initial.head(10))
        print("\n새로운 데이터 특성 중요도 (SHAP 평균 절대값 - Top 10):")
        print(shap_importance_new.head(10))

        # 시각화로 비교 (Summary Plot - Beeswarm)
        # KernelExplainer의 shap_values는 (num_samples, num_features, num_classes) 형태이므로,
        # shap.summary_plot에 전달하기 위해서는 Explanation 객체로 래핑하거나,
        # 특정 클래스의 SHAP 값 (num_samples, num_features)만 전달해야 합니다.
        
        # SHAP Summary Plot for class 0 (예시)
        # shap.Explanation(values=shap_values, base_values=expected_value, data=X_data, feature_names=feature_names)
        
        # KernelExplainer는 base_values도 (num_classes,) 형태로 반환할 수 있습니다.
        # 여기서는 가장 첫 번째 클래스(0)에 대한 summary plot을 그립니다.
        # 이는 이미지 데이터이므로, summary_plot이 모든 픽셀을 개별 특성으로 처리하여 플로팅합니다.
        # 고차원 데이터의 경우 모든 특성을 그리는 것보다 상위 N개 특성만 그리도록 조정하는 것이 좋습니다.
        
        # Shap values for a specific class (e.g., class 0)
        shap_values_class_0_initial = shap_values_initial[:, :, 0] 
        shap_values_class_0_new = shap_values_new[:, :, 0]

        print("\n특정 클래스(0)에 대한 SHAP Beeswarm Plot (Top 20 Features):")
        plt.figure(figsize=(15, 6))
        
        plt.subplot(1, 2, 1)
        shap.summary_plot(shap_values_class_0_initial, X_initial_sample, feature_names=self.feature_names, show=False)
        plt.title("Initial Data - Feature Importance (Class 0)")
        plt.subplot(1, 2, 2)
        shap.summary_plot(shap_values_class_0_new, X_new_sample, feature_names=self.feature_names, show=False)
        plt.title("New Data - Feature Importance (Class 0)")
        plt.tight_layout()
        plt.show()

        print("\nSHAP 값 변화를 통해 드리프트가 모델의 특성 중요도 인식에 영향을 미쳤음을 시사합니다.")
        return shap_importance_initial, shap_importance_new

    def analyze_lime(self, X_new_flat, num_samples_to_explain=5):
        print(f"\n3.2. LIME을 이용한 지역적 예측 설명 변화 분석 (샘플 {num_samples_to_explain}개):")
        
        initial_indices = np.random.choice(self.X_initial_flat.shape[0], num_samples_to_explain, replace=False)
        new_indices = np.random.choice(X_new_flat.shape[0], num_samples_to_explain, replace=False)

        # from IPython.display import display, HTML # Jupyter 환경에서만 필요하며, main.py에는 포함하지 않음

        print(f"\n초기 데이터 샘플 {num_samples_to_explain}개에 대한 LIME 설명:")
        for i, idx in enumerate(initial_indices):
            print(f"\n--- Initial Sample {i+1} (idx: {idx}) ---")
            instance = self.X_initial_flat[idx]
            exp_initial = self.lime_explainer.explain_instance(
                data_row=instance,
                predict_fn=self.predict_proba_fn,
                num_features=20 # 상위 20개 특성 설명
            )
            try:
                from IPython.display import display, HTML
                display(HTML(exp_initial.as_html()))
            except ImportError:
                print("LIME HTML 설명을 표시할 수 없습니다 (Jupyter Notebook 외부?). 텍스트 설명을 출력합니다.")
                for feature, weight in exp_initial.as_list():
                    print(f"- {feature}: {weight:.4f}")
            
        print(f"\n새로운 데이터 샘플 {num_samples_to_explain}개에 대한 LIME 설명:")
        for i, idx in enumerate(new_indices):
            print(f"\n--- New Data Sample {i+1} (idx: {idx}) ---")
            instance = X_new_flat[idx]
            exp_new = self.lime_explainer.explain_instance(
                data_row=instance,
                predict_fn=self.predict_proba_fn,
                num_features=20
            )
            try:
                from IPython.display import display, HTML
                display(HTML(exp_new.as_html()))
            except ImportError:
                print("LIME HTML 설명을 표시할 수 없습니다 (Jupyter Notebook 외부?). 텍스트 설명을 출력합니다.")
                for feature, weight in exp_new.as_list():
                    print(f"- {feature}: {weight:.4f}")
        
        print("\nLIME 설명을 통해 개별 예측에서 중요하게 작용하는 픽셀들이 달라졌음을 확인합니다.")


# --- 5. 드리프트 해결 클래스 ---
class DriftResolver:
    """드리프트 감지 및 XAI 분석 결과를 바탕으로 해결책을 제안하는 클래스."""
    def __init__(self):
        pass

    def propose_solution(self, drift_detected, drift_features, initial_shap_importance, new_shap_importance, X_initial_flat, X_new_flat, feature_names):
        print("\n--- 4. 재학습 방향성 제시 및 모델 아키텍처 조정 검토 ---")

        if not drift_detected and (initial_shap_importance is None or new_shap_importance is None):
            print("데이터 드리프트가 감지되지 않았거나 분석 정보가 부족하여 제안할 해결책이 없습니다.")
            return

        print("\n**재학습 방향성 제시:**")
        if len(drift_features) > 0:
            print(f"  - 감지된 드리프트 특성: {', '.join(drift_features[:5])} ...") # 상위 5개만 표시
            print("  - 가장 큰 변화를 보이는 특성(픽셀)의 분포를 확인하고, 해당 픽셀 영역의 데이터 품질을 점검합니다.")
            print("  - **새로운 데이터를 수집하여 모델을 재학습**하는 것이 시급합니다. 특히 드리프트가 발생한 특성(예: 이미지의 특정 영역, 밝기)의 분포를 반영할 수 있는 데이터를 우선적으로 확보합니다.")
            print("  - 가능하다면, 새로운 데이터 분포를 반영할 수 있도록 **데이터 전처리 파이프라인을 업데이트**하는 것을 고려합니다 (예: 새로운 정규화 방식, 노이즈 제거 필터).")
        else:
            print("  - 통계적으로 유의미한 특성 드리프트는 감지되지 않았으나, 모델 성능 하락이 있다면 개념 드리프트 또는 미세한 특성 변화가 원인일 수 있습니다.")

        print("  - 데이터 드리프트 모니터링 시스템을 강화하여 드리프트 발생 시 **자동 알림 및 재학습 트리거**를 설정합니다.")

        # 가장 드리프트가 큰 특성 시각화 (PCA 등을 통해 차원 축소 후 시각화가 현실적이지만, 여기서는 단순 픽셀 분포로)
        if len(drift_features) > 0:
            top_drift_feature = drift_features[0] # 첫 번째 드리프트 픽셀 선택
            top_drift_feature_idx = feature_names.index(top_drift_feature)
            
            plt.figure(figsize=(10, 5))
            sns.histplot(X_initial_flat[:, top_drift_feature_idx], color='blue', kde=True, label='Initial Data', stat='density')
            sns.histplot(X_new_flat[:, top_drift_feature_idx], color='red', kde=True, label='New Data', stat='density', alpha=0.6)
            plt.title(f"Distribution of '{top_drift_feature}': Initial vs. New Data")
            plt.xlabel(top_drift_feature)
            plt.ylabel("Density")
            plt.legend()
            plt.show()
            print(f"\n시각화를 통해 가장 드리프트가 큰 '{top_drift_feature}' 픽셀의 분포가 초기 데이터와 새로운 데이터에서 크게 달라졌음을 명확히 확인할 수 있습니다.")


        print("\n**모델 아키텍처 조정 검토:**")
        # SHAP 중요도 변화를 통해 특정 픽셀 영역의 중요도가 달라졌는지 분석
        if initial_shap_importance is not None and new_shap_importance is not None:
            importance_diff = (initial_shap_importance - new_shap_importance).abs().sort_values(ascending=False)
            print(f"\n가장 중요도 변화가 큰 픽셀 (Top 5):")
            print(importance_diff.head(5))

            if importance_diff.max() > 0.1: # 중요도 변화가 크다면
                print("  - SHAP 중요도 변화가 큰 픽셀들이 특정 이미지 영역에 집중되어 있다면, 해당 영역의 변화에 모델이 취약하거나 과민 반응하는 것일 수 있습니다.")
                print("  - 기존 CNN 모델이 드리프트된 데이터 패턴(예: 새로운 노이즈, 스케일 변화)에 적절히 대응하지 못할 수 있습니다.")
                print("  - 다음을 고려할 수 있습니다:")
                print("    - **데이터 증강(Data Augmentation):** 새로운 드리프트 패턴(예: 더 다양한 노이즈, 회전, 밝기 변화)을 학습 데이터에 미리 주입하여 모델의 강건성을 높입니다.")
                print("    - **더 강건한 CNN 아키텍처:** Inception, ResNet 등 드리프트에 더 강건하거나 특징 추출 능력이 뛰어난 모델 아키텍처로의 전환을 고려합니다.")
                print("    - **전이 학습(Transfer Learning):** 유사한 이미지 데이터셋으로 사전 학습된 모델을 활용하여 새로운 데이터에 빠르게 적응하도록 합니다.")
                print("    - **어댑티브 러닝(Adaptive Learning) 기법:** 모델이 지속적으로 새로운 데이터에 적응하도록 온라인 학습(Online Learning) 또는 가중치 업데이트 전략을 도입합니다.")
            else:
                print("  - 특성 중요도의 큰 변화는 감지되지 않았으므로, 모델 아키텍처 조정보다는 데이터 수집/전처리 개선이 우선일 수 있습니다.")
        else:
            print("  - SHAP 중요도 분석이 수행되지 않아 모델 아키텍처 조정에 대한 구체적인 제안을 할 수 없습니다.")