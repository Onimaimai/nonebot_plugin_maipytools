import json
from pathlib import Path
from .config import plugin_config
from .database import Database

def migrate_from_json():
    """从JSON文件迁移数据到SQLite数据库"""
    data_dir = Path(plugin_config.maimai_data_path)
    json_file = data_dir / "user_data.json"
    db = Database()
    
    if not json_file.exists():
        print("未找到user_data.json文件，无需迁移")
        return
    
    try:
        # 读取JSON数据
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        
        # 迁移数据到数据库
        for user_id, user_info in json_data.items():
            # 从user_info中移除user_id，避免参数重复
            if 'user_id' in user_info:
                del user_info['user_id']
            db.update_user_data(user_id, **user_info)
        
        print(f"成功迁移 {len(json_data)} 条用户数据到数据库")
        
        # 备份原JSON文件
        backup_file = json_file.with_suffix(".json.bak")
        json_file.rename(backup_file)
        print(f"原JSON文件已备份为: {backup_file}")
        
    except Exception as e:
        print(f"迁移过程中出现错误: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_from_json() 