from typing import Optional
from pydantic import BaseModel, ConfigDict 
from datetime import datetime

class UserData(BaseModel):
    """用户数据模型"""
    user_id: str
    credentials: Optional[str] = None
    import_token: Optional[str] = None
    last_updated: datetime = datetime.now()

    # 使用新的配置方式
    model_config = ConfigDict(
        from_attributes=True,
    )
