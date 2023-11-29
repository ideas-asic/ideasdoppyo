
import pandas as pd

register = pd.read_json('nm2_asic_conf.json')
data = register['consolidated_model'][0]
print(data)