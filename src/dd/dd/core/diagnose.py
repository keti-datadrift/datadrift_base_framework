import pandas as pd
import numpy as np

def run(filepath):
    df = pd.read_csv(filepath)
    report = {
        "missing_values": df.isnull().sum().sum(),
        "duplicates": df.duplicated().sum(),
        "outliers": (np.abs(df - df.mean()) > (2 * df.std())).sum().sum()
    }
    print(report)