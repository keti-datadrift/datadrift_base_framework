import pandas as pd
import uuid
from sqlalchemy.orm import Session
from ..models import Dataset
from .dvc_service import dvc_add_file

def create_dataset(db: Session, uploaded_file):
    file_path, dvc_info = dvc_add_file(uploaded_file)
    df = pd.read_csv(file_path)

    dataset = Dataset(
        id=str(uuid.uuid4()),
        name=uploaded_file.filename,
        type="csv",
        size=len(df),
        rows=df.shape[0],
        cols=df.shape[1],
        preview={"head": df.head(5).to_dict()},
        dvc_path=file_path,
        version="v1"
    )

    db.add(dataset)
    db.commit()
    return dataset