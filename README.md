# pcrjjc2

本插件是[pcrjjc](https://github.com/lulu666lulu/pcrjjc)重置版，不需要使用其他后端api，但是需要自行配置客户端  

**本项目基于AGPL v3协议开源**

## 配置方法

1. 拿个不用的号登录PCR，然后把data/data/tw.sonet.princessconnect/shared_prefs/tw.sonet.princessconnect.v2.playerprefs.xml复制到该目录

   注意：每个服对应一个账号配置文件，并且每个号至少得开启加好友功能，四个服就要四份不同服的文件

2. 安装依赖：

   ```
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

3. 配置account.json设置代理：localhost就行，只要改端口，自行更换和你代理软件代理的端口一样就行，是代理端口哦，不是软件监听端口，开PAC模式不改变系统代理就行

4. 在create_img.py中更改你所在的服务器名称

5. 开启插件，并重启Hoshino即可食用

## 命令

| 关键词             | 说明                                                     |
| ------------------ | -------------------------------------------------------- |
| 竞技场绑定 uid     | 绑定竞技场排名变动推送，默认双场均启用，仅排名降低时推送 |
| 竞技场查询 uid     | 查询竞技场简要信息（绑定后无需输入uid）                  |
| 停止竞技场订阅     | 停止战斗竞技场排名变动推送                               |
| 停止公主竞技场订阅 | 停止公主竞技场排名变动推送                               |
| 启用竞技场订阅     | 启用战斗竞技场排名变动推送                               |
| 启用公主竞技场订阅 | 启用公主竞技场排名变动推送                               |
| 删除竞技场订阅     | 删除竞技场排名变动推送绑定                               |
| 竞技场订阅状态     | 查看排名变动推送绑定状态                                 |
| 详细查询 uid       | 查询账号详细状态（绑定后无需输入uid）                    |
| 查询群数           | 查询bot所在群的数目                                      |
| 查询竞技场订阅数   | 查询绑定账号的总数量                                     |
| 清空竞技场订阅     | 清空所有绑定的账号(仅限主人)                             |

## 支持版本

目前支持游戏版本：3.1.0

和之前的pcrjjc2一样，若后续游戏版本更新请自己打开`pcrclient.py`文件第18行

```
    'APP-VER' : '3.1.0',
```

修改游戏版本为当前最新，然后重启hoshinobot即可

## 更新日志

2022-2-21：详细查询整合为两张精美图片，分别为个人资料卡图片以及支援界面图片

## 图片预览

![FQ~} OTM$L20L6DAEI~RN`K](https://user-images.githubusercontent.com/71607036/154994397-fc1a4f89-4e10-4380-94bc-687868adfa9b.PNG)

![4@{%Z%591B` YE1%}H0E7@1](https://user-images.githubusercontent.com/71607036/154994414-483cef8b-cce5-4764-8557-3a149a7a344e.jpg)
