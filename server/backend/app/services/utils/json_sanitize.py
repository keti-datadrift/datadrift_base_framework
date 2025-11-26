import math

def clean_json_value(x):
    if x is None:
        return None
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    if isinstance(x, dict):
        return {k: clean_json_value(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean_json_value(v) for v in x]
    return x