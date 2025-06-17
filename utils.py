import json
import os
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from .config import plugin_config
from .models import UserData
from .database import Database
from .migrate import migrate_from_json

class MaimaiAPI:
    def __init__(self):
        self.base_url = plugin_config.maimai_api_url
        self.data_dir = Path(plugin_config.maimai_data_path)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db = Database()
        
        # 用户数据迁移
        #migrate_from_json()
        
        self.user_data = self.db.get_all_users()

    def get_user_data(self, user_id: str) -> Optional[UserData]:
        """获取用户数据"""
        return self.db.get_user_data(user_id)

    def update_user_data(self, user_id: str, **kwargs) -> UserData:
        """更新用户数据"""
        user_data = self.db.update_user_data(user_id, **kwargs)
        self.user_data[user_id] = user_data
        return user_data

    async def get_credentials(self, qrcode: str) -> str:
        """通过二维码获取credentials"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.base_url}/arcade/qrcode?qrcode={qrcode}') as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('credentials')
                else:
                    raise Exception(f"请求失败: {response.status}")

    async def get_regions(self, credentials: str) -> List[Dict]:
        """获取区域信息"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.base_url}/arcade/regions?credentials={credentials}') as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"请求失败: {response.status}")

    async def get_player_info(self, credentials: str) -> Dict:
        """获取玩家信息"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.base_url}/arcade/players?credentials={credentials}') as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"请求失败: {response.status}")
                    
    async def get_scores(self, credentials: str, session: aiohttp.ClientSession = None) -> Dict:
        """获取玩家分数信息"""
        use_local_session = False
        if session is None:
            session = aiohttp.ClientSession()
            use_local_session = True
        try:
            async with session.get(f'{self.base_url}/arcade/scores?credentials={credentials}') as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"请求失败: {response.status}")
        finally:
            if use_local_session:
                await session.close()
                
    async def import_scores(self, import_token: str, scores: dict, session: aiohttp.ClientSession = None) -> bool:
        """将分数数据发送到接口"""
        use_local_session = False
        if session is None:
            session = aiohttp.ClientSession()
            use_local_session = True
        try:
            url = f"{self.base_url}/divingfish/scores"
            params = {'credentials': import_token}
            async with session.post(url, params=params, json=scores) as response:
                return response.status == 200
        finally:
            if use_local_session:
                await session.close()
                
    async def post_scores_to_divingfish(self, import_token: str, scores: dict, session: aiohttp.ClientSession = None) -> bool:
        """导入分数到diving-fish"""
        use_local_session = False
        if session is None:
            session = aiohttp.ClientSession(headers={"Accept-Encoding": "gzip"})
            use_local_session = True
        try:
            headers = {"Import-Token": import_token}
            async with session.post(
                'https://proxy.yuzuchan.xyz/maimaidxprober/player/update_records',
                headers=headers,
                json=scores
            ) as response:
                return response.status == 200
        finally:
            if use_local_session:
                await session.close()
                
    async def verify_divingfish_token(self, import_token: str) -> bool:
        """验证水鱼token是否有效"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://www.diving-fish.com/api/maimaidxprober/player/records',
                headers={"Import-Token": import_token}
            ) as response:
                return response.status == 200
                

def format_region_info(regions: List[Dict]) -> List[Dict]:
    """格式化区域信息"""
    formatted_regions = []
    
    for region in regions:
        created_at = datetime.fromisoformat(region.get('created_at')).strftime('%Y-%m-%d %H:%M:%S')
        
        formatted_region = {
            '区域ID': region.get('region_id', '未知'),
            '区域名称': region.get('region_name', '未知'),
            '游玩次数': region.get('play_count', 0),
            '首次游玩时间': created_at
        }
        formatted_regions.append(formatted_region)
    
    return sorted(formatted_regions, key=lambda x: x['游玩次数'], reverse=True)

def format_player_info(player: Dict) -> str:
    """格式化玩家信息"""
    info = []
    info.append(f"玩家名称: {player.get('name', '未知')}")
    info.append(f"登录状态: {'已登录' if player.get('is_login') else '未登录'}")
    info.append(f"Rating: {player.get('rating', 0)}")
    
    icon = player.get('icon')
    name_plate = player.get('name_plate')
    if name_plate:
        info.append(f"\n名牌信息: {name_plate}")
    
    trophy = player.get('trophy')
    if trophy:
        info.append(f"\n称号信息: {trophy}")
    
    return "\n".join(info)

def format_scores(scores: List[Dict]) -> List[Dict]:
    """格式化分数信息"""
    formatted_scores = []
    
    fc_map = {
        0: "app",
        1: "ap",
        2: "fcp",
        3: "fc"
    }
    
    fs_map = {
        0: "sync",
        1: "fs",
        2: "fsp",
        3: "fsd",
        4: "fsdp"
    }
    
    for score in scores:
        formatted_score = {
            "achievements": score.get("achievements", 0),
            "dxScore": score.get("dx_score", 0),
            "fc": fc_map.get(score.get("fc"), ""),
            "fs": fs_map.get(score.get("fs"), ""),
            "level_index": score.get("level_index", 0),
            "title": score.get("song_name", ""),
            "type": "DX" if score.get("type") == "dx" else "SD"
        }
        formatted_scores.append(formatted_score)
    
    return formatted_scores 