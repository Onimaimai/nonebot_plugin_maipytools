from nonebot import on_command
from nonebot import on_regex
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
import aiohttp
import asyncio
import os
from .utils import MaimaiAPI, format_region_info, format_player_info, format_scores
from datetime import datetime

__plugin_meta__ = PluginMetadata(
    name="舞萌工具",
    description="舞萌工具",
    usage="""
    指令列表：
    maibind 你的二维码识别内容 - 绑定舞萌账号
    maitoken 你的成绩导入token - 绑定水鱼账号
    舞萌地区 / mair - 查看游玩地区统计
    舞萌信息 / maii - 查看玩家账号信息
    水鱼更新 / ccb - 上传成绩到水鱼查分器
    """.strip()
)

# 创建API实例
api = MaimaiAPI()

# 绑定账号
bind = on_command("maibind", priority=5, block=False)
@bind.handle()
async def handle_bind(event: MessageEvent, args: Message = CommandArg()):
    user_id = str(event.user_id)
    qrcode = args.extract_plain_text().strip()
    
    if not qrcode:
        #await bind.finish("请发送：\nmaibind 二维码识别内容")
        base_dir = "/root/"
        image_filename = f"maibind.jpg"
        image_path = os.path.join(base_dir, image_filename)
        if not os.path.exists(image_path):
            return
        with open(image_path, "rb") as f:
            picbytes = f.read()
        await token.finish("请打开公众号点击玩家二维码\n打开二维码长按识别复制内容"+MessageSegment.image(picbytes))
    
    credentials = await api.get_credentials(qrcode)
        
    api.update_user_data(user_id, credentials=credentials)
    await bind.finish()


# 查看区域信息
regions = on_command("mair",aliases={"mairegion","舞萌地区"}, priority=5, block=True)
@regions.handle()
async def handle_regions(event: MessageEvent):
    # 检查是否at了其他用户
    at_user_id = None
    if event.reply and event.reply.sender:
        at_user_id = str(event.reply.sender.user_id)
    else:
        for seg in event.message:
            if seg.type == "at":
                at_user_id = str(seg.data.get("qq"))
                break
    user_id = at_user_id if at_user_id else str(event.user_id)
    user_data = api.get_user_data(user_id)
    if not user_data or not user_data.credentials:
        if at_user_id:
            await regions.finish(f"对方未绑定账号，无法查询。",reply_message=True)
        else:
            await regions.finish("请发送：\nmaibind 二维码识别内容",reply_message=True)
    region_data = await api.get_regions(user_data.credentials)
    formatted_regions = format_region_info(region_data)
    msg = []
    total_play_count = 0
    earliest_time = None
    for idx, region in enumerate(formatted_regions):
        msg.extend([
            f"{region['区域名称']}：",
            f"游玩次数: {region['游玩次数']}",
            f"首次游玩: {region['首次游玩时间']}"
        ])
        if idx != len(formatted_regions) - 1:
            msg.append("")  # 城市间空一行
        total_play_count += region['游玩次数']
        try:
            t = datetime.strptime(region['首次游玩时间'], '%Y-%m-%d %H:%M:%S')
            if earliest_time is None or t < earliest_time:
                earliest_time = t
        except Exception:
            pass
    # 计算入坑天数
    if earliest_time:
        from datetime import datetime as dt
        days = (dt.now() - earliest_time).days
        msg.append(f"\n已入坑{days}天，累计游玩{total_play_count}次")
    else:
        msg.append(f"\n累计游玩{total_play_count}次")
    # 移除末尾空行（如果有）
    while msg and msg[-1] == "":
        msg.pop()
    await regions.finish("\n".join(msg),reply_message=True)


# 查看玩家信息
info = on_command("maic",aliases={"maicheck","舞萌状态"}, priority=5, block=True)
@info.handle()
async def handle_info(event: MessageEvent):
    user_id = str(event.user_id)
    user_data = api.get_user_data(user_id)
    
    if not user_data or not user_data.credentials:
        await info.finish("请发送：\nmaibind 二维码识别内容",reply_message=True) #"请先@我使用 mai bind 绑定舞萌公众号"
    

    player_data = await api.get_player_info(user_data.credentials)
    formatted_info = format_player_info(player_data)
    await info.finish(formatted_info,reply_message=True)


# 设置导入token
token = on_command("maitoken", priority=5)
@token.handle()
async def handle_token(event: MessageEvent, args: Message = CommandArg()):
    user_id = str(event.user_id)
    import_token = args.extract_plain_text().strip()
    
    if not import_token:
        #await token.finish("请发送：\nmaitoken 水鱼成绩导入token")
        base_dir = "/root/"
        image_filename = f"maitoken.jpg"
        image_path = os.path.join(base_dir, image_filename)
        if not os.path.exists(image_path):
            return
        with open(image_path, "rb") as f:
            picbytes = f.read()
        await token.finish("请登录水鱼查分器复制你的token\nhttps://www.diving-fish.com/maimaidx/prober/"+MessageSegment.image(picbytes))
    
    # 验证token是否有效
    if not await api.verify_divingfish_token(import_token):
        await token.finish()
    
    api.update_user_data(user_id, import_token=import_token)
    await token.finish()


# 导入分数
import_scores = on_regex(r"^(导|水鱼更新|更新水鱼|ccb|b50|B50)$", priority=10, block=False)
@import_scores.handle()
async def handle_import(event: MessageEvent):
    await import_scores.send("收到")
    user_id = str(event.user_id)
    user_data = api.get_user_data(user_id)
    # 判断是否为b50指令
    is_b50 = str(event.get_plaintext()).strip().lower() == "b50" or str(event.get_plaintext()).strip().lower() == "B50"
    
    if not user_data or not user_data.credentials:
        #await import_scores.send("收到")
        if not is_b50:
            base_dir = "/root/"
            image_filename = f"maibind.jpg"
            image_path = os.path.join(base_dir, image_filename)
            if not os.path.exists(image_path):
                return
            with open(image_path, "rb") as f:
                picbytes = f.read()
            await import_scores.finish([MessageSegment.reply(event.message_id), MessageSegment.text("请发送：\nmaibind 二维码识别内容"), MessageSegment.image(picbytes)])
        return
        
    if not user_data.import_token:
        #await import_scores.send("收到")
        if not is_b50:
            base_dir = "/root/"
            image_filename = f"maitoken.jpg"
            image_path = os.path.join(base_dir, image_filename)
            if not os.path.exists(image_path):
                return
            with open(image_path, "rb") as f:
                picbytes = f.read()
            await import_scores.finish([MessageSegment.reply(event.message_id), MessageSegment.text("请发送：\nmaitoken 你的token\nhttps://www.diving-fish.com/maimaidx/prober/"), MessageSegment.image(picbytes)])
        return
    
    #await import_scores.send("正在更新")
    
    async with aiohttp.ClientSession() as session:
        scores = await api.get_scores(user_data.credentials, session)
        task1 = api.post_scores_to_divingfish(user_data.import_token, format_scores(scores), session)
        task2 = api.import_scores(user_data.import_token, scores, session)
        done, pending = await asyncio.wait(
            [task1, task2],
            return_when=asyncio.FIRST_COMPLETED
        )
        success = None
        exception = None
        for task in done:
            try:
                success = task.result()
                break
            except Exception as e:
                exception = e
        for task in pending:
            task.cancel()
        if success:
            if not is_b50:
                await import_scores.finish("水鱼已更新", reply_message=True)
            else:
                await import_scores.finish()
        else:
            raise exception if exception else Exception("水鱼更新失败")
            await import_scores.finish()

