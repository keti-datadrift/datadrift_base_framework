#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

import pickle

def run(model1, model2):
    with open(model1, "rb") as f1, open(model2, "rb") as f2:
        m1 = pickle.load(f1)
        m2 = pickle.load(f2)

    print(f"📊 모델 비교 결과:")
    print(f"- {model1}: {m1.score}")
    print(f"- {model2}: {m2.score}")