import pandas as pd

def run(filepath):
    df = pd.read_csv(filepath)
    df.fillna(df.mean(), inplace=True)
    df = df[~df.duplicated()]
    df = df[(df - df.mean()).abs() <= (2 * df.std())]

    new_filepath = filepath.replace(".csv", "_cleaned.csv")
    df.to_csv(new_filepath, index=False)
    print(f"✅ 데이터 품질 개선 완료: {new_filepath}")