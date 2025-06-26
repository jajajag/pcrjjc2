from .api_config import API
from .create_img import generate_info_pic, generate_support_pic
from .pcrclient import pcrclient, ApiException, get_headers
from .playerpref import decryptxml
from .safeservice import SafeService
from asyncio import Lock, sleep
from copy import deepcopy
from datetime import datetime
from hoshino import logger, priv, get_bot
from hoshino.typing import MessageSegment, NoticeSession
from hoshino.util import pic2b64
from json import load, dump
from nonebot import get_bot
from os.path import dirname, join, exists
from traceback import format_exc
import calendar
import json
import os
import random
import requests
import time
# JAG: 如果有则导入CHARA_NAME，否则设置为空
try: from hoshino.modules.priconne._pcr_data import CHARA_NAME
except: CHARA_NAME = {}

sv_help = '''
【订阅默认关闭，需要发指令手动开启】
[竞技场绑定 uid] 绑定竞技场排名变动推送，默认双场均启用，仅排名降低时推送
[竞技场查询 (uid)] 查询竞技场简要信息
[详细查询 (uid)] 查询账号详细信息
[公会查询 公会名 会长名] 查询指定公会排名和分数
[排名查询 页数] 根据排名查询公会排名和分数
[(启用|停止)公会订阅] (启用|停止)公会日界排名推送
[(启用|停止)竞技场订阅] (启用|停止)战斗竞技场排名变动推送
[(启用|停止)公主竞技场订阅] (启用|停止)公主竞技场排名变动推送
[竞技场订阅状态] 查看排名变动推送绑定状态
[删除竞技场订阅] 删除竞技场排名变动推送绑定
[查询群数] 查询bot所在群的数目
[查询竞技场订阅数] 查询绑定账号的总数量
[清空竞技场订阅] 清空所有绑定的账号(仅限主人)
'''.strip()

# headers文件，启动时不存在就创建
header_path = os.path.join(os.path.dirname(__file__), 'headers.json')
if not os.path.exists(header_path):
    default_headers = get_headers()
    with open(header_path, 'w', encoding='UTF-8') as f:
        json.dump(default_headers, f, indent=4, ensure_ascii=False)

sv = SafeService('竞技场推送_tw', help_=sv_help, bundle='pcr查询')

@sv.on_fullmatch('竞技场帮助', only_to_me=False)
async def send_jjchelp(bot, ev):
    await bot.send(ev, f'{sv_help}')

@sv.on_fullmatch('查询群数', only_to_me=False)
async def group_num(bot, ev):
    self_ids = bot._wsr_api_clients.keys()
    for sid in self_ids:
        gl = await bot.get_group_list(self_id=sid)
        msg = f"本Bot目前正在为【{len(gl)}】个群服务"
    await bot.send(ev, f'{msg}')

# 读取绑定配置
curpath = dirname(__file__)
config = join(curpath, 'binds.json')
root = {
    'arena_bind' : {},
    # JAG: Add clan binds
    'clan_bind' : []
}
if exists(config):
    with open(config) as fp:
        root = load(fp)
binds = root['arena_bind']

# 读取代理配置
with open(join(curpath, 'account.json')) as fp:
    pinfo = load(fp)

# 一些变量初始化
cache = {}
client = None

# 设置异步锁保证线程安全
lck = Lock()
captcha_lck = Lock()
qlck = Lock()

# Forked from https://github.com/azmiao/pcrjjc_tw_new/commit/42346b79d9da112ad8fd84070e19729126c79899
# 全局缓存的client登陆 | 减少协议握手次数
client_cache = None
# JAG: 全局缓存clan_id
clan_id_cache = None

# 获取配置文件
def get_client():
    # Forked from https://github.com/azmiao/pcrjjc_tw_new/commit/42346b79d9da112ad8fd84070e19729126c79899
    global client_cache
    acinfo = {'admin': ''}
    if client_cache is None:
        acinfo = decryptxml(join(curpath,
                                 'tw.sonet.princessconnect.v2.playerprefs.xml'))
        client = pcrclient(acinfo['UDID'], acinfo['SHORT_UDID_lowBits'],
                           acinfo['VIEWER_ID_lowBits'], acinfo['TW_SERVER_ID'],
                           pinfo['proxy'])
        client_cache = client
    return client_cache, acinfo

# JAG: 缓存并返回clan_id
async def get_clan_id():
    global clan_id_cache
    if clan_id_cache is None:
        res = await query(API['clan_self'])
        clan_id_cache = res['clan']['detail']['clan_id']
    return clan_id_cache

# JAG: 把api的调用放到外面
async def query(api: tuple, *args):
    # JAG: api is a tuple of (api_url, api_params)
    client, acinfo = get_client()
    async with qlck:
        while client.shouldLogin:
            await client.login()
        res = (await client.callapi(api[0], api[1](*args)))
        return res

def save_binds():
    with open(config, 'w') as fp:
        dump(root, fp, indent=4)

@sv.on_fullmatch('查询竞技场订阅数', only_to_me=False)
async def pcrjjc_number(bot, ev):
    global binds, lck

    async with lck:
        await bot.send(ev, f'当前竞技场已订阅的账号数量为【{len(binds)}】个')

@sv.on_fullmatch('清空竞技场订阅', only_to_me=False)
async def pcrjjc_del(bot, ev):
    global binds, lck

    async with lck:
        if not priv.check_priv(ev, priv.SUPERUSER):
            await bot.send(ev, 
                '抱歉，您的权限不足，只有bot主人才能进行该操作！')
            return
        else:
            num = len(binds)
            binds.clear()
            save_binds()
            await bot.send(ev, f'已清空全部【{num}】个已订阅账号！')

@sv.on_rex(r'^竞技场绑定\s*([2-4]\d{9})$')
async def on_arena_bind(bot, ev):
    global binds, lck

    async with lck:
        uid = str(ev['user_id'])
        last = binds[uid] if uid in binds else None

        binds[uid] = {
            'id': ev['match'].group(1),
            'uid': uid,
            'gid': str(ev['group_id']),
            # JAG: By default we do subscribe arena and grand_arena
            #'arena_on': last is None or last['arena_on'],
            'arena_on': False,
            #'grand_arena_on': last is None or last['grand_arena_on'],
            'grand_arena_on': False,
        }
        save_binds()

    await bot.finish(ev, '竞技场绑定成功', at_sender=True)

@sv.on_rex(r'^竞技场查询\s*([2-4]\d{9})?$')
async def on_query_arena(bot, ev):
    global binds, lck

    robj = ev['match']
    uid = robj.group(1)

    async with lck:
        if uid is None:
            uid = str(ev['user_id'])
            if not uid in binds:
                await bot.finish(ev, '您还未绑定竞技场', at_sender=True)
                return
            else:
                uid = binds[uid]['id']
        try:
            res = await query(API['arena_profile'], uid)
            
            last_login_time = int (res['user_info']['last_login_time'])
            last_login_date = time.localtime(last_login_time)
            last_login_str = time.strftime('%Y-%m-%d %H:%M:%S',last_login_date)
            # JAG: Change nick name to character name
            id_favorite = int(str(res['favorite_unit']['id'])[0:4])
            user_name_text = (CHARA_NAME[id_favorite][0]
                              if id_favorite in CHARA_NAME else '未知角色')
            
            await bot.finish(ev, 
#f'''昵称：{res['user_info']["user_name"]}
f'''头像：{user_name_text}
jjc排名：{res['user_info']["arena_rank"]}
pjjc排名：{res['user_info']["grand_arena_rank"]}
最后登录：{last_login_str}
''', at_sender=False)
        except ApiException as e:
            await bot.finish(ev, f'查询出错，{e}', at_sender=True)

@sv.on_rex(r'^详细查询\s*([2-4]\d{9})?$')
async def on_query_arena_all(bot, ev):
    global binds, lck

    robj = ev['match']
    uid = robj.group(1)

    async with lck:
        if uid is None:
            uid = str(ev['user_id'])
            if not uid in binds:
                await bot.finish(ev, '您还未绑定竞技场', at_sender=True)
                return
            else:
                uid = binds[uid]['id']
        try:
            res = await query(API['arena_profile'], uid)
            # 通过log显示信息
            sv.logger.info('开始生成竞技场查询图片...')
            # result_image = await generate_info_pic(res, cx)
            result_image = await generate_info_pic(res, pinfo)
            # 转base64发送，不用将图片存本地
            result_image = pic2b64(result_image)
            result_image = MessageSegment.image(result_image)
            # JAG: Do NOT send support info
            #result_support = await generate_support_pic(res)
            # 转base64发送，不用将图片存本地
            #result_support = pic2b64(result_support)
            #result_support = MessageSegment.image(result_support)
            sv.logger.info('竞技场查询图片已准备完毕！')
            try:
                #await bot.finish(ev,
                #        f"\n{str(result_image)}\n{result_support}",
                #        at_sender=True)
                await bot.finish(ev, f"\n{str(result_image)}", at_sender=True)
            except Exception as e:
                sv.logger.info("do nothing")
        except ApiException as e:
            await bot.finish(ev, f'查询出错，{e}', at_sender=True)

@sv.on_rex('(启用|停止)(公主)?竞技场订阅')
async def change_arena_sub(bot, ev):
    global binds, lck

    key = 'arena_on' if ev['match'].group(2) is None else 'grand_arena_on'
    uid = str(ev['user_id'])

    async with lck:
        if not uid in binds:
            await bot.send(ev,'您还未绑定竞技场',at_sender=True)
        else:
            binds[uid][key] = ev['match'].group(1) == '启用'
            save_binds()
            await bot.finish(ev, f'{ev["match"].group(0)}成功', at_sender=True)

# 台服建议注释掉该命令，以防止与b服的验证码输入产生冲突，导致验证码输入无响应。
# @on_command('/pcrval')
async def validate(session):
    global binds, lck, validate
    client, acinfo = get_client()
    if session.ctx['user_id'] == acinfo['admin']:
        validate = session.ctx['message'].extract_plain_text().strip()[8:]
        captcha_lck.release()

@sv.on_prefix('删除竞技场订阅')
async def delete_arena_sub(bot,ev):
    global binds, lck

    uid = str(ev['user_id'])

    if ev.message[0].type == 'at':
        if not priv.check_priv(ev, priv.SUPERUSER):
            await bot.finish(ev, '删除他人订阅请联系维护', at_sender=True)
            return
        uid = str(ev.message[0].data['qq'])
    elif (len(ev.message) == 1 and ev.message[0].type == 'text'
          and not ev.message[0].data['text']):
        uid = str(ev['user_id'])

    if not uid in binds:
        await bot.finish(ev, '未绑定竞技场', at_sender=True)
        return

    async with lck:
        binds.pop(uid)
        save_binds()

    await bot.finish(ev, '删除竞技场订阅成功', at_sender=True)

@sv.on_fullmatch('竞技场订阅状态')
async def send_arena_sub_status(bot,ev):
    global binds, lck
    uid = str(ev['user_id'])
    
    if not uid in binds:
        await bot.send(ev,'您还未绑定竞技场', at_sender=True)
    else:
        info = binds[uid]
        await bot.finish(ev,
f'''
当前竞技场绑定ID：{info['id']}
竞技场订阅：{'开启' if info['arena_on'] else '关闭'}
公主竞技场订阅：{'开启' if info['grand_arena_on'] else '关闭'}
''', at_sender=True)


# minutes是刷新频率，可按自身服务器性能输入其他数值，可支持整数、小数
@sv.scheduled_job('interval', minutes=3)
async def on_arena_schedule():
    global cache, binds, lck
    bot = get_bot()
    
    bind_cache = {}

    async with lck:
        bind_cache = deepcopy(binds)

    for user in bind_cache:
        info = bind_cache[user]
        try:
            # JAG: Skip if both subscriptions are off
            if (not info['arena_on']) and (not info['grand_arena_on']):
                continue
            sv.logger.info(f'querying {info["id"]} for {info["uid"]}')
            res = await query(API['arena_profile'], info['id'])
            res = (res['user_info']['arena_rank'],
                    res['user_info']['grand_arena_rank'])

            if user not in cache:
                cache[user] = res
                continue

            last = cache[user]
            cache[user] = res

            if res[0] > last[0] and info['arena_on']:
                await bot.send_group_msg(
                    group_id = int(info['gid']),
                    message = f'[CQ:at,qq={info["uid"]}] jjc：{last[0]}->{res[0]} ▼{res[0]-last[0]}'
                )

            if res[1] > last[1] and info['grand_arena_on']:
                await bot.send_group_msg(
                    group_id = int(info['gid']),
                    message = f'[CQ:at,qq={info["uid"]}] pjjc：{last[1]}->{res[1]} ▼{res[1]-last[1]}'
                )
        except ApiException as e:
            sv.logger.info(f'对{info["id"]}的检查出错\n{format_exc()}')
            if e.code == 6:

                async with lck:
                    binds.pop(user)
                    save_binds()
                sv.logger.info(f'已经自动删除错误的uid={info["id"]}')
        except:
            sv.logger.info(f'对{info["id"]}的检查出错\n{format_exc()}')

@sv.on_notice('group_decrease.leave')
async def leave_notice(session: NoticeSession):
    global lck, binds
    uid = str(session.ctx['user_id'])
    
    async with lck:
        if uid in binds:
            binds.pop(uid)
            save_binds()

# 由于apkimage网站的pcr_tw大概每次都是12点左右更新的
# 因此这里每天13点左右自动更新版本号
# JAG: 搜内一般维护到6pm，我们改到6pm更新版本号
@sv.scheduled_job('cron', hour='18', minute='1')
async def update_ver():
    header_path = os.path.join(os.path.dirname(__file__), 'headers.json')
    new_headers = get_headers()
    # JAG: Return if the version in the header is not updated
    if new_headers['APP-VER'] == default_headers['APP-VER']: return
    with open(header_path, 'w', encoding='UTF-8') as f:
        json.dump(default_headers, f, indent=4, ensure_ascii=False)
    # Clear the cache
    global client_cache
    client_cache = None
    sv.logger.info(f'pcr-jjc2-tw的游戏版本已更新至最新') 

CLAN_RANK_ERROR = '未获得公会排名信息，可能在结算中或未参加会战'

# JAG: 通过公会名和会长名查询公会排名（使用raw input否则某些字符查不到）
@sv.on_rex(r'^公会查询\s*(\S+)?\s*(\S+)?$', normalize=False)
async def on_query_clan_name(bot, ev):
    robj = ev['match']
    clan_name, leader_name = robj.group(1), robj.group(2)
    self_clan_id = await get_clan_id()

    if clan_name is None:
        await bot.finish(ev, '请输入您想查询的公会名', at_sender=True)
    try:
        # JAG: 1. Search clan by name
        res = await query(API['clan_search'], clan_name)
        clans = [clan for clan in res['list']]
        if not clans:
            await bot.finish(ev, '未找到含有该名称的公会', at_sender=True)
        # JAG: 2. Filter clans by leader name if provided
        elif len(clans) > 1:
            clans = [clan for clan in clans if leader_name 
                     and leader_name in clan['leader_name']]
            if len(clans) != 1:
                show_clans = [f"\n{clan['clan_name']} -> {clan['leader_name']}"
                          for clan in res['list']]
                show_clans_message = ''.join(show_clans)
                await bot.finish(ev, 
                    ('未找到或找到多个符合条件的公会，请检查会长名：'
                     + show_clans_message), at_sender=True)
        # JAG: 3. Query clan by clan_id
        clan_id = clans[0]['clan_id']
        res = await query(API['clan_others'], clan_id)
        rank = res['clan']['detail']['current_period_ranking']
        if not rank: await bot.finish(ev, CLAN_RANK_ERROR, at_sender=True)
        # JAG: 4. Query clan by page
        res = await query(API['clan_ranking'], self_clan_id, (rank - 1) // 10)
        if (not res['period_ranking'] 
            or len(res['period_ranking']) < (rank - 1) % 10 + 1):
            await bot.finish(ev, CLAN_RANK_ERROR, at_sender=True)
        clan = res['period_ranking'][(rank - 1) % 10]
        await bot.finish(ev, 
                f'\n{clan["rank"]} {clan["clan_name"]} {clan["damage"]}',
                at_sender=True)
    except ApiException as e:
        await bot.finish(ev, f'查询出错，{e}', at_sender=True)

# JAG: 根据页数查询公会排名
@sv.on_rex(r'^排名查询\s*(\d+)?$')
async def on_query_clan_page(bot, ev):
    robj = ev['match']
    page = robj.group(1)
    self_clan_id = await get_clan_id()

    if page is None:
        await bot.finish(ev, '请输入您想查询的公会页数', at_sender=True)
    try:
        # JAG: Query clan by page
        res = await query(API['clan_ranking'], self_clan_id, int(page) - 1)
        ranks = [f'\n{clan["rank"]} {clan["clan_name"]} {clan["damage"]}'
                 for clan in res['period_ranking']]
        if not ranks: await bot.finish(ev, CLAN_RANK_ERROR, at_sender=True)
        await bot.finish(ev, ''.join(ranks), at_sender=True)
    except ApiException as e:
        await bot.finish(ev, f'查询出错，{e}', at_sender=True)

@sv.on_rex('(启用|停止)公会订阅')
async def change_clan_sub(bot, ev):
    global lck, root

    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '抱歉，您的权限不足，只有管理员才能进行该操作！')

    async with lck:
        group_id = str(ev['group_id'])
        if ev['match'].group(1) == '启用' and group_id not in root['clan_bind']:
            root['clan_bind'].append(group_id)
        else:
            root['clan_bind'] = [x for x in root['clan_bind'] if x != group_id]
        save_binds()
        await bot.finish(ev, f'{ev["match"].group(0)}成功', at_sender=True)

# JAG: 广播前60名的公会到订阅的群
async def broadcast_rankings():
    # JAG: 0. Initialize parameters (we assume at least one sid is available)
    global lck, root
    async with lck: 
        group_list = deepcopy(root['clan_bind'])
    bot = get_bot()
    sid = random.choice(bot.get_self_ids())
    self_clan_id = await get_clan_id()
    # JAG: 1. Check if today is within the last four days of the month
    now = datetime.now()
    hour, day, month, year = now.hour, now.day, now.month, now.year
    last_day = calendar.monthrange(year, month)[1]
    if day < last_day - 3 or (day != last_day and hour != 4):
        return
    # JAG: 2. Query top 60 clans
    try:
        ranks = [
            f'\n{clan["rank"]} {clan["clan_name"]} {clan["damage"]}'
            for page in range(6)
            for clan in (await query(
                API['clan_ranking'], self_clan_id, page))['period_ranking']
        ]
    except ApiException as e:
        logger.info(f'查询排名信息出错: {e}')
        return
    message = now.strftime('%Y-%m-%d %H:%M') + '排名' + ''.join(ranks)
    # JAG: 3. Broadcast rankings to all subscribed groups
    for group_id in group_list:
        await sleep(0.5)
        try:
            await bot.send_group_msg(self_id=sid, group_id=group_id,
                                     message=message)
        except CQHttpError as e:
            logger.info(f'发送排名信息到群{group_id}失败: {e}')

sv.scheduled_job('cron', hour='4', minute='55')(broadcast_rankings)
sv.scheduled_job('cron', hour='23', minute='55')(broadcast_rankings)
