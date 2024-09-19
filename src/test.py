from datetime import datetime
from pydantic import BaseModel

class DataModel(BaseModel):
    StartTime: datetime

sample_data = {
    "StartTime" : "2024-09-17 15:15:03+04:00"
}

data = DataModel(**sample_data)

print(f"StartTime = {data.StartTime}")