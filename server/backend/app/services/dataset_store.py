# dataset_store.py
import pandas as pd
from uuid import uuid4

class DatasetStore:
    def __init__(self):
        self.data = {}
        self.meta = {}

    def add_dataset(self, file):
        ds_id = str(uuid4())
        df = pd.read_csv(file.file)

        self.data[ds_id] = df
        self.meta[ds_id] = {
            "id": ds_id,
            "name": file.filename,
            "rows": len(df),
            "cols": len(df.columns),
            "columns": list(df.columns)
        }
        return ds_id

    def get(self, id):
        return self.data.get(id)

    def get_meta(self, id):
        return self.meta.get(id)

    def list_datasets(self):
        return list(self.meta.values())

# ← 추가: 싱글턴 인스턴스
store = DatasetStore()