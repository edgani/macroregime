from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent
METRIC_FAMILIES=pd.read_csv(HERE/'metric_registry_v4.csv').to_dict('records')
