from datetime import datetime, timedelta, timezone
import json
from time import sleep
from typing import Tuple
import requests
from urllib.parse import urlparse
from Crypto.Cipher import DES
from config import StbConfig, CommonConfig
from hashlib import md5
from collections import namedtuple
from storage import Storage
import re
import os

def pkcs7(s: str) -> str:
    bs: int = DES.block_size
    return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)


def getAuthenticator(userid: str, password: str, stbid: str, mac: str, encry_token: str, salt: str) -> str:
    salty: bytes = (password + salt).encode('ascii')
    payload: bytes = pkcs7("99999${token}${user}${stb}$127.0.0.1${mac}$$CTC".format(
        token=encry_token,
        user=userid,
        stb=stbid,
        mac=mac
    )).encode('ascii')

    key: bytes = bytes(md5(salty).hexdigest()[:8], encoding='ascii')
    return (DES.new(key, DES.MODE_ECB).encrypt(payload)).hex().upper()


def stb_login(storage: Storage, common_config: CommonConfig, config: StbConfig) -> bool:
    headers: dict = {
        'User-Agent': config.ua
    }

    print("第一步，登陆IPTV服务器")

    response = requests.get(
        "http://{server}/EDS/jsp/AuthenticationURL?UserID={user}&Action=Login".format(
            server=config.server, user=config.userid),
        headers=headers)

    if not response.ok:
        print("登陆至IPTV服务器失败")
        return False

    # 因为有可能被重定向，所以我们获取重定向后的url
    server: str = urlparse(response.url).netloc

    print("第二步，获取EncryptToken")

    response = requests.post(
        "http://{server}/EPG/jsp/authLoginHWCTC.jsp".format(
            server=server),
        data={
            'UserID': config.userid,
            'VIP': config.vip
        },
        headers=headers)

    if not response.ok:
        print("获取EncryptToken失败")
        return False

    tokenMatch: list = re.findall(
        r'var EncryptToken = "([0-9A-F]{32}?)";', response.text)

    if len(tokenMatch) == 0:
        print("提取EncryptToken失败")
        return False

    encrypt_token: str = tokenMatch[0]
    authenticator: str = getAuthenticator(
        config.userid,
        config.password,
        config.stbid,
        config.mac,
        encrypt_token,
        config.salt
    )

    print("第三步，进行授权认证")

    response = requests.post(
        "http://{server}/EPG/jsp/ValidAuthenticationHWCTC.jsp".format(
            server=server),
        data={
            'UserID': config.userid,
            'Lang': config.lang,
            'SupportHD': config.support_hd,
            'NetUserID': config.net_userid,
            'Authenticator': authenticator,
            'STBType': config.stb_type,
            'STBVersion': config.stb_version,
            'conntype': config.conntype,
            'STBID': config.stbid,
            'templateName': config.template_name,
            'areaId': config.areaid,
            'userToken': encrypt_token,
            'userGroupId': config.usergroupid,
            'productPackageId': config.product_packageid,
            'mac': config.mac,
            'UserField': config.user_field,
            'SoftwareVersion': config.software_version,
            'IsSmartStb': config.is_smartstb,
            'desktopId': config.desktopid,
            'stbmaker': config.stbmarker,
            'XMPPCapability': config.xmpp_capability,
            'ChipID': config.chipid,
            'VIP': config.vip
        },
        headers=headers)

    if not response.ok:
        print("授权认证失败")
        return False

    cookie_value: str = response.cookies['JSESSIONID']

    if not cookie_value:
        print("获取cookie失败")
        return False

    cookie: str = '{name}={value}; {name}={value};'.format(
        name='JSESSIONID', value=cookie_value)

    headers['cookie'] = cookie

    tokenMatch: list = re.findall(
        r'name="UserToken" value="([0-9a-zA-Z]{32}?)"', response.text)

    if len(tokenMatch) == 0:
        print("提取UserToken失败")
        return False

    user_token: str = tokenMatch[0]

    print("第四步，获取频道列表")

    response = requests.post(
        "http://{server}/EPG/jsp/getchannellistHWCTC.jsp".format(
            server=server),
        data={
            'conntype': config.conntype,
            'UserToken': user_token,
            'tempKey': '',  # 不用计算也能用
            'stbid': config.stbid,
            'SupportHD': config.support_hd,
            'UserID': config.userid,
            'Lang': config.lang
        },
        headers=headers)

    if not response.ok:
        print("获取频道列表失败")
        return False

    regex = re.compile(
        r'iRet = Authentication.CTCSetConfig\(\'Channel\',\'ChannelID=.+\);')
    matches: list[str] = regex.findall(response.text)

    print("频道列表获取完成，当前获取到{count}个频道".format(count=len(matches)))

    re_channel_id = re.compile(r'ChannelID="([0-9]+?)"')
    re_channel_name = re.compile(r'ChannelName="(.+?)"')
    re_user_channel_id = re.compile(r'UserChannelID="([0-9]+?)"')
    re_rstp_url = re.compile(r'ChannelURL=".+?\|(rtsp.+?)"')
    re_igmp_url = re.compile(r'ChannelURL="(igmp.+?)\|.+?"')

    filter = len(config.channels) > 0

    ChannelInfo = namedtuple(
        "ChannelInfo", "id,name,group,user_number,logo,igmp_url,rtsp_url")
    channel_infos: list[ChannelInfo] = []

    print("第五步，提取频道信息")

    if filter:
        for line in matches:
            try:
                source_id = int(re_channel_id.findall(line)[0])
                channel_info = config.channels[source_id]
                channel_name = channel_info.name
                channel_group = channel_info.group
                user_number = channel_info.user_number
                rtsp_url = re_rstp_url.findall(line)[0]
                igmp_url = re_igmp_url.findall(line)[0]
                logo = channel_info.logo
            except:
                continue
            else:
                channel_infos.append(ChannelInfo(
                    id=source_id,
                    name=channel_name,
                    user_number=user_number,
                    logo=logo,
                    group=channel_group,
                    igmp_url=igmp_url,
                    rtsp_url=rtsp_url
                ))

    print("频道信息提取完成，提取了{count}个频道".format(count=len(channel_infos)))

    print("第六步，生成播放列表")

    with open(os.path.join(common_config.data_dir, 'igmp.m3u'), 'w', encoding='utf-8') as igmp_file:
        with open(os.path.join(common_config.data_dir, 'rstp.m3u'), 'w', encoding='utf-8') as rstp_file:
            igmp_file.write('#EXTM3U' + '\n')
            rstp_file.write('#EXTM3U' + '\n')
            for channel_info in channel_infos:
                info_line = '#EXTINF:-1 tvg-id="{channel_id}" tvg-name="{channel_name}" tvg-chno="{user_number}" tvg-logo="{logo}" group-title="{group_name}", {channel_name}\n'.format(
                    channel_id=channel_info.id,
                    user_number=channel_info.user_number,
                    channel_name=channel_info.name,
                    group_name=channel_info.group,
                    logo=channel_info.logo
                )
                igmp_file.write(info_line)
                rstp_file.write(info_line)

                igmp_file.write("{url}/{proto}/{igmp}\n".format(
                    url=common_config.udpxy_url,
                    proto=common_config.udpxy_protocal,
                    igmp=channel_info.igmp_url
                ))

                rstp_file.write("{rstp}\n".format(rstp=channel_info.rtsp_url))

    print("播放列表已生成")

    print("第七步，获取节目单服务器地址")

    response = requests.post(
        "http://{server}/EPG/jsp/default/en/Category.jsp".format(
            server=server),
        data={
            'directplay': 0,
            'lastchannelNo': 'null',
            'isComeFromPredeal': 1,
            'joinFlag': 0
        },
        headers=headers)

    if not response.ok:
        print("获取节目单服务器地址失败")
        return False

    match: list = re.findall(r'var serverUrl = \'(.+?)\'', response.text)

    if len(match) == 0:
        print("提取节目单服务器地址失败")
        return False

    epg_server = urlparse(match[0]).netloc

    print("第八步，获取频道信息")

    response = requests.get(
        "http://{server}/pub/galaxy_simple/vendor/data/channel.js".format(server=epg_server))

    if not response.ok:
        print("获取频道信息失败")
        return False

    regex = re.compile(
        r'\{[\w\W]*?name:[\w\W]*?data: (\[[\w\W]*?\])[\w\W]*?\}')

    matches: list = regex.findall(
        re.sub(r'//.+?\n', "", re.sub(r'/\*.+?\*/', '', response.text)))

    channel_ids: list[Tuple[str, int, str]] = []
    for match in matches:
        match: str = match.replace(
            "\n", ""
        ).replace(
            "\r", ""
        ).replace(
            " ", ""
        ).replace(
            'data', '"data"'
        ).replace(
            'channelId', '"channelId"'
        ).replace(
            'name', '"name"'
        ).replace(
            'num', '"num"'
        ).replace(
            'realNum', '"realNum"'
        ).replace(
            'mediaId', '"mediaId"'
        ).replace(
            'is4k', '"is4k"'
        ).replace(
            'vip', '"vip"'
        ).replace(
            ',]', ']'
        )

        dataList: list = json.loads(match)
        for data in dataList:
            try:
                channel_config = config.channels[data["realNum"]]
                channel_ids.append(
                    (channel_config.name, int(data["realNum"]), data["channelId"]))
            except:
                continue

    today = datetime.now(tz=timezone(timedelta(hours=+8))) # 兼容未设定timezone或timezone不为东八区的情况
    regex = re.compile("[0-9]{8}=(\{.+\});")

    print("第九步，获取节目单")

    for channel_name, channel_id, source_id in channel_ids:
        for i in range(-7, 2):
            sleep(1)
            date_to_query = (today + timedelta(days=i))
            date_str = date_to_query.strftime('%Y-%m-%d')
            print("开始获取频道{channel}时间为{date}的节目单".format(
                channel=channel_name, date=date_str))
            response = requests.get("http://{server}/pub/json/{date}/{source_id}.js".format(
                server=epg_server,
                date=date_str,
                source_id=source_id
            ))

            if not response.ok:
                print("获取频道{channel}时间为{date}的节目单失败".format(
                    channel=channel_name, date=date_str))
                continue

            epg = response.text.replace(" ", "")
            match: list[str] = regex.findall(epg)
            if len(match) == 0:
                print("频道{channel}时间为{date}无节目单数据".format(
                    channel=channel_name, date=date_str))
                continue
            print("开始保存频道{channel}时间为{date}的节目单".format(
                channel=channel_name, date=date_str))
            storage.save(epg_date=date_to_query, channel_id=channel_id,
                         channel_name=channel_name, json_str=match[0])
            print("频道{channel}时间为{date}的节目单已保存".format(
                channel=channel_name, date=date_str))

    print("最终步，生成epg电子节目单")

    storage.epg_generator(os.path.join(common_config.data_dir, 'epg.xml'),
                          today + timedelta(days=-7), today + timedelta(days=2))
