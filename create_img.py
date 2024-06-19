from PIL import Image, ImageDraw, ImageFont, ImageColor
from ..priconne import chara
import time
from pathlib import Path
import zhconv
from hoshino.aiorequests import run_sync_func
# JAG: Import character names from hoshino
try:
    from hoshino.modules.priconne._pcr_data import CHARA_NAME, CHARA_PROFILE
    # Find correct clan name using a new dict
    REAL_CHARA_NAME = {CHARA_NAME[i][0]: i  for i in CHARA_NAME}
    REAL_CHARA_NAME = {REAL_CHARA_NAME[i]: REAL_CHARA_NAME[i[:i.find('(')]] \
            if i[:i.find('(')] in REAL_CHARA_NAME \
            else REAL_CHARA_NAME[i] for i in REAL_CHARA_NAME}
except:
    # If not exist, use an empty dict instead
    CHARA_NAME, CHARA_PROFILE = {}, {}

path = Path(__file__).parent # 获取文件所在目录的绝对路径
font_cn_path = str(path / 'fonts' / 'SourceHanSansCN-Medium.otf')
# Path是路径对象，必须转为str之后ImageFont才能读取
font_tw_path = str(path / 'fonts' / 'pcrtwfont.ttf')

def _TraditionalToSimplified(hant_str: str):
    '''
    Function: 将 hant_str 由繁体转化为简体
    '''
    return zhconv.convert(str(hant_str), 'zh-hans')

def _cut_str(obj: str, sec: int):
    """
    按步长分割字符串
    """
    return [obj[i: i+sec] for i in range(0, len(obj), sec)]

def _calculate_knight_rank(value, experience_list):
    """
    计算公主骑士等级
    """
    for index, exp in enumerate(experience_list):
        if value <= exp:
            return index
    return -1

def _generate_info_pic_internal(data, pinfo):
    '''
    个人资料卡生成
    '''
    im = Image.open(path / 'img' / 'template.png') # 图片模板
    im_frame = Image.open(path / 'img' / 'frame.png') # 头像框
    try:
        # 截取第1位到第4位的字符
        id_favorite = int(str(data['favorite_unit']['id'])[0:4])
    except:
        id_favorite = 1000 # 一个？角色
    pic_dir = chara.fromid(id_favorite).icon.path
    user_avatar = Image.open(pic_dir)
    user_avatar = user_avatar.resize((90, 90))
    im.paste(user_avatar, (44, 150), mask=user_avatar)
    im_frame = im_frame.resize((100, 100))
    im.paste(im=im_frame, box=(39, 145), mask=im_frame)

    cn_font = ImageFont.truetype(font_cn_path, 18) # Path是路径对象，必须转为str之后ImageFont才能读取
    # tw_font = ImageFont.truetype(str(font_tw_path), 18) # 字体有点问题，暂时别用
    
    font = cn_font # 选择字体
    
    cn_font_resize = ImageFont.truetype(font_cn_path, 16)
    # tw_font_resize = ImageFont.truetype(font_tw_path, 16)
    # 字体有点问题，暂时别用
    
    font_resize = cn_font_resize #选择字体

    draw = ImageDraw.Draw(im)
    font_black = (77, 76, 81, 255)

    # 资料卡 个人信息
    user_name_text = _TraditionalToSimplified(data["user_info"]["user_name"])

    # JAG: Change nick name to character name
    user_name_text = CHARA_NAME[id_favorite][0] \
            if id_favorite in CHARA_NAME else '未知角色'
    team_level_text = _TraditionalToSimplified(data["user_info"]["team_level"])
    total_power_text = _TraditionalToSimplified(
        data["user_info"]["total_power"])
    # JAG: Add princess_knight_rank
    princess_knight_exp = data["user_info"]["princess_knight_rank_total_exp"]
    princess_knight_rank = _calculate_knight_rank(
            princess_knight_exp, pinfo['experience_knight_rank'])
    princess_knight_rank_text = _TraditionalToSimplified(princess_knight_rank)
    clan_name_text = _TraditionalToSimplified(data["clan_name"])

    # JAG: Set clan name to game clan name
    if id_favorite in REAL_CHARA_NAME \
            and REAL_CHARA_NAME[id_favorite] in CHARA_PROFILE \
            and '公会' in CHARA_PROFILE[REAL_CHARA_NAME[id_favorite]]:
        clan_name_text = CHARA_PROFILE[REAL_CHARA_NAME[id_favorite]]['公会']
    else:
        clan_name_text = '？？？'
    user_comment_arr = _cut_str(_TraditionalToSimplified(
        data["user_info"]["user_comment"]), 25)

    # JAG: Set comment to default
    #user_comment_arr = _cut_str('请多指教。', 25)
    last_login_time_text = _TraditionalToSimplified(time.strftime(
        "%Y/%m/%d %H:%M:%S", time.localtime(
            data["user_info"]["last_login_time"]))).split(' ')

    draw.text((194, 120), user_name_text, font_black, font)

    # JAG: 设置服务器名称
    viewer_id = str(data["user_info"]["viewer_id"])
    if len(viewer_id) == 10 and viewer_id[0] == '2':
        server_name = '真步真步王国'
    elif len(viewer_id) == 10 and viewer_id[0] == '3':
        server_name = '破晓之星'
    elif len(viewer_id) == 10 and viewer_id[0] == '4':
        server_name = '小小甜心'
    else:
        server_name = '美食殿堂'

    # JAG: Original position for level and clan_name: 168, 250
    w, h = font_resize.getsize(team_level_text)
    draw.text((568 - w, 170), team_level_text, font_black, font_resize)
    w, h = font_resize.getsize(total_power_text)
    draw.text((568 - w, 210), total_power_text, font_black, font_resize)
    w, h = font_resize.getsize(princess_knight_rank_text)
    draw.text((568 - w, 250), princess_knight_rank_text, font_black, 
              font_resize)
    w, h = font_resize.getsize(clan_name_text)
    draw.text((568 - w, 290), clan_name_text, font_black, font_resize)
    # JAG: Do not display user comment
    #for index, value in enumerate(user_comment_arr):
    #    draw.text((170, 310 + (index * 22)), value, font_black, font_resize)
    # JAG: Original position for last login time: 350, 392
    draw.text((34, 330), last_login_time_text[0] + "\n" +
              last_login_time_text[1], font_black, font_resize)
    draw.text((34, 372), server_name, font_black, font_resize)

    # 资料卡 冒险经历
    normal_quest_text = _TraditionalToSimplified(
        data["quest_info"]["normal_quest"][2])
    hard_quest_text = _TraditionalToSimplified(
        data["quest_info"]["hard_quest"][2])
    very_hard_quest_text = _TraditionalToSimplified(
        data["quest_info"]["very_hard_quest"][2])
    # JAG: Add talent_quest
    talent_list = ["火", "水", "风", "光", "暗"]
    talent_quest = data["quest_info"]["talent_quest"]
    talent_quest_sorted = sorted(talent_quest, key=lambda x: x['talent_id'])
    clear_count_list = [talent_list[i] \
            + str(talent_quest_sorted[i]['clear_count']) for i in range(5)]
    talent_quest_text = _TraditionalToSimplified(
            '/'.join(map(str, clear_count_list)))

    # JAG: Original position for the text: 498, 530
    w, h = font_resize.getsize(normal_quest_text)
    draw.text((550 - w, 470), normal_quest_text, font_black, font_resize)
    w, h = font_resize.getsize("H" + hard_quest_text +
                           "/VH" + very_hard_quest_text)
    draw.text((550 - w, 500), "H" + hard_quest_text +
              "/VH", font_black, font_resize)
    w, h = font_resize.getsize(very_hard_quest_text)
    draw.text((550 - w, 500), very_hard_quest_text, font_black, font_resize)
    w, h = font_resize.getsize(talent_quest_text)
    draw.text((550 - w, 530), talent_quest_text, font_black, font_resize)

    arena_group_text = _TraditionalToSimplified(
        data["user_info"]["arena_group"])
    arena_time_text = _TraditionalToSimplified(time.strftime(
        "%Y/%m/%d", time.localtime(data["user_info"]["arena_time"])))
    arena_rank_text = _TraditionalToSimplified(data["user_info"]["arena_rank"])
    grand_arena_group_text = _TraditionalToSimplified(
        data["user_info"]["grand_arena_group"])
    grand_arena_time_text = _TraditionalToSimplified(time.strftime(
        "%Y/%m/%d", time.localtime(data["user_info"]["grand_arena_time"])))
    grand_arena_rank_text = _TraditionalToSimplified(
        data["user_info"]["grand_arena_rank"])

    w, h = font_resize.getsize(arena_time_text)
    draw.text((550 - w, 598), arena_time_text, font_black, font_resize)
    w, h = font_resize.getsize(arena_group_text+"场")
    draw.text((550 - w, 630), arena_group_text+"场", font_black, font_resize)
    w, h = font_resize.getsize(arena_rank_text+"名")
    draw.text((550 - w, 662), arena_rank_text+"名", font_black, font_resize)
    w, h = font_resize.getsize(grand_arena_time_text)
    draw.text((550 - w, 704), grand_arena_time_text, font_black, font_resize)
    w, h = font_resize.getsize(grand_arena_group_text+"场")
    draw.text((550 - w, 738), grand_arena_group_text+"场", font_black, font_resize)
    w, h = font_resize.getsize(grand_arena_rank_text+"名")
    draw.text((550 - w, 772), grand_arena_rank_text+"名", font_black, font_resize)

    unit_num_text = _TraditionalToSimplified(data["user_info"]["unit_num"])
    open_story_num_text = _TraditionalToSimplified(
        data["user_info"]["open_story_num"])

    w, h = font_resize.getsize(unit_num_text)
    draw.text((550 - w, 844), unit_num_text, font_black, font_resize)
    w, h = font_resize.getsize(open_story_num_text)
    draw.text((550 - w, 880), open_story_num_text, font_black, font_resize)

    tower_cleared_floor_num_text = _TraditionalToSimplified(
        data["user_info"]["tower_cleared_floor_num"])
    tower_cleared_ex_quest_count_text = _TraditionalToSimplified(
        data["user_info"]["tower_cleared_ex_quest_count"])

    w, h = font_resize.getsize(tower_cleared_floor_num_text+"阶")
    draw.text((550 - w, 949), tower_cleared_floor_num_text +
              "阶", font_black, font_resize)
    w, h = font_resize.getsize(tower_cleared_ex_quest_count_text)
    draw.text((550 - w, 984), tower_cleared_ex_quest_count_text,
              font_black, font_resize)

    # JAG: Display viewer_id in a proper way
    #viewer_id_arr = _cut_str(_TraditionalToSimplified(
    #        data["user_info"]["viewer_id"]), 3)
    viewer_id_arr = f'{data["user_info"]["viewer_id"]:,}'.split(',')
    viewer_id_str = "  ".join(viewer_id_arr)
    w, h = font.getsize(viewer_id_str)
    draw.text((138 + (460 - 138) / 2 - w / 2, 1058), viewer_id_str,
              (255, 255, 255, 255), font)

    return im

def _friend_support_position(fr_data, im, fnt, rgb, im_frame, bbox):
    '''
    好友支援位
    '''
    # 合成头像
    im_yuansu = Image.open(path / 'img' / 'yuansu.png') # 一个支援ui模板
    id_friend_support = int(str(fr_data['unit_data']['id'])[0:4])
    pic_dir = chara.fromid(id_friend_support).icon.path
    avatar = Image.open(pic_dir)
    avatar = avatar.resize((115, 115))
    im_yuansu.paste(im=avatar, box=(28, 78), mask=avatar)
    im_frame = im_frame.resize((128, 128))
    im_yuansu.paste(im=im_frame, box=(22, 72), mask=im_frame)

    # 合成文字信息
    yuansu_draw = ImageDraw.Draw(im_yuansu)
    icon_name_text = _TraditionalToSimplified(chara.fromid(id_friend_support).name)
    icon_LV_text = str(fr_data['unit_data']['unit_level']) # 写入文本必须是str格式
    icon_rank_text = str(fr_data['unit_data']['promotion_level'])
    yuansu_draw.text(xy=(167, 36.86), text=icon_name_text, font=fnt, fill=rgb)
    yuansu_draw.text(xy=(340, 101.8), text=icon_LV_text, font=fnt, fill=rgb)
    yuansu_draw.text(xy=(340, 159.09), text=icon_rank_text, font=fnt, fill=rgb)
    im.paste(im=im_yuansu, box=bbox) # 无A通道的图不能输入mask

    return im

def _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox):
    '''
    地下城及战队支援位
    '''
    # 合成头像
    im_yuansu = Image.open(path / 'img' / 'yuansu.png') # 一个支援ui模板
    id_clan_support = int(str(clan_data['unit_data']['id'])[0:4])
    pic_dir = chara.fromid(id_clan_support).icon.path
    avatar = Image.open(pic_dir)
    avatar = avatar.resize((115, 115))
    im_yuansu.paste(im=avatar, box=(28, 78), mask=avatar)
    im_frame = im_frame.resize((128, 128))
    im_yuansu.paste(im=im_frame, box=(22, 72), mask=im_frame)

    # 合成文字信息
    yuansu_draw = ImageDraw.Draw(im_yuansu)
    icon_name_text = _TraditionalToSimplified(chara.fromid(id_clan_support).name)
    icon_LV_text = str(clan_data['unit_data']['unit_level']) # 写入文本必须是str格式
    icon_rank_text = str(clan_data['unit_data']['promotion_level'])
    yuansu_draw.text(xy=(167, 36.86), text=icon_name_text, font=fnt, fill=rgb)
    yuansu_draw.text(xy=(340, 101.8), text=icon_LV_text, font=fnt, fill=rgb)
    yuansu_draw.text(xy=(340, 159.09), text=icon_rank_text, font=fnt, fill=rgb)
    im.paste(im=im_yuansu, box=bbox) # 无A通道的图不能输入mask

    return im

def _generate_support_pic_internal(data):
    '''
    支援界面图片合成
    '''
    im = Image.open(path / 'img' / 'support.png') # 支援图片模板
    im_frame = Image.open(path / 'img' / 'frame.png') # 头像框

    fnt = ImageFont.truetype(font=font_cn_path, size=30)
    rgb = ImageColor.getrgb('#4e4e4e')

    # 判断玩家设置的支援角色应该存在的位置
    for fr_data in data['friend_support_units']: # 若列表为空，则不会进行循环
        if fr_data['position'] == 1: # 好友支援位1
            bbox = (1284, 156)
            im = _friend_support_position(fr_data, im, fnt, rgb, im_frame, bbox)
        elif fr_data['position'] == 2: # 好友支援位2
            bbox = (1284, 459)
            im = _friend_support_position(fr_data, im, fnt, rgb, im_frame, bbox)

    for clan_data in data['clan_support_units']:
        if clan_data['position'] == 1: # 地下城位置1
            bbox = (43, 156)
            im = _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox)
        elif clan_data['position'] == 2: # 地下城位置2
            bbox = (43, 459)
            im = _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox)
        elif clan_data['position'] == 3: # 战队位置1
            bbox = (665, 156)
            im = _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox)
        elif clan_data['position'] == 4: # 战队位置2
            bbox = (665, 459)
            im = _clan_support_position(clan_data, im, fnt, rgb, im_frame, bbox)
    
    return im

async def generate_support_pic(*args, **kwargs):
    return await run_sync_func(_generate_support_pic_internal, *args, **kwargs)

async def generate_info_pic(*args, **kwargs):
    return await run_sync_func(_generate_info_pic_internal, *args, **kwargs)
