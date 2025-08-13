#!/usr/bin/env python3

import pandas as pd
import numpy as np
import json
from datetime import datetime

def make_serializable(obj):
    """Convert numpy/pandas types to JSON serializable types"""
    import pandas as pd
    import numpy as np
    
    if isinstance(obj, pd.Timestamp):
        if pd.isna(obj):
            return None
        return obj.isoformat()
    elif isinstance(obj, np.datetime64):
        if pd.isna(obj):
            return None
        return pd.Timestamp(obj).isoformat()
    elif pd.isna(obj):  # Handle pandas NaT and other pandas NA types
        return None
    elif hasattr(obj, "item"):  # numpy scalars
        return obj.item()
    elif hasattr(obj, "tolist"):  # numpy arrays
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(v) for v in obj]
    else:
        return obj

# Test data with problematic types
test_data = {
    "timestamp": pd.Timestamp("2024-01-01 10:00:00"),
    "nat": pd.NaT,
    "datetime64": np.datetime64("2024-01-01 10:00:00"),
    "regular_string": "test",
    "regular_number": 42,
    "nested_dict": {
        "inner_timestamp": pd.Timestamp("2024-01-01 11:00:00"),
        "inner_nat": pd.NaT
    },
    "list_with_timestamps": [
        pd.Timestamp("2024-01-01 12:00:00"),
        pd.NaT,
        "regular_string"
    ]
}

print("Original data:")
print(test_data)
print()

try:
    # This should fail
    json.dumps(test_data)
    print("ERROR: json.dumps should have failed!")
except Exception as e:
    print(f"Expected error with json.dumps: {e}")
    print()

try:
    # This should work
    clean_data = make_serializable(test_data)
    print("Cleaned data:")
    print(clean_data)
    print()
    
    # This should now work
    json_str = json.dumps(clean_data)
    print("JSON serialization successful!")
    print(f"JSON: {json_str}")
    
except Exception as e:
    print(f"Error with make_serializable: {e}")
