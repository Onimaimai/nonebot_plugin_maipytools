from pydantic import BaseModel, ConfigDict
from nonebot import get_driver

class Config(BaseModel):
    """Plugin Config"""
    model_config = ConfigDict(extra='ignore')
    
    maimai_api_url: str = "http://100.73.27.14:12345"
    maimai_data_path: str = "./data/maipytools"

# 获取驱动配置并转换为字典
driver_config = get_driver().config.dict()

# 解析配置
plugin_config = Config.model_validate(driver_config)
