from configparser import ConfigParser
from collections import Counter, namedtuple

ChannelConfig = namedtuple(
    'ChannelConfig',
    'id,user_number,name,group,logo,epgid')

UdpxyConfig = namedtuple(
    'UdpxyConfig',
    'udpxy_url,udpxy_protocal')


class StbConfig:
    server: str
    ua: str
    userid: str
    password: str
    salt: str
    lang: str
    support_hd: str
    net_userid: str
    stb_type: str
    stb_version: str
    conntype: str
    stbid: str
    template_name: str
    areaid: str
    usergroupid: str
    product_packageid: str
    mac: str
    user_field: str
    software_version: str
    is_smartstb: str
    desktopid: str
    stbmarker: str
    xmpp_capability: str
    chipid: str
    vip: str
    channels: dict[int, ChannelConfig] = {}


def read_stb_config(path: str) -> tuple[UdpxyConfig, StbConfig]:
    config = StbConfig()

    parser = ConfigParser()
    parser.read(path, encoding='utf-8')

    sections = parser.sections()
    sections.remove('common')
    sections.remove('iptv')

    udpxy_url = parser.get('common', 'udpxy_url', raw=True).strip()
    udpxy_protocal = parser.get('common', 'udpxy_protocal', raw=True).strip()

    config.server = parser.get('iptv', 'Server', raw=True).strip()
    config.ua = parser.get('iptv', 'UA', raw=True).strip()
    config.userid = parser.get('iptv', 'UserID', raw=True).strip()
    config.password = parser.get('iptv', 'Password', raw=True).strip()
    config.salt = parser.get('iptv', 'Salt', raw=True).strip()
    config.lang = parser.get('iptv', 'Lang', raw=True).strip()
    config.support_hd = parser.get('iptv', 'SupportHD', raw=True).strip()
    config.net_userid = parser.get('iptv', 'NetUserID', raw=True).strip()
    config.stb_type = parser.get('iptv', 'STBType', raw=True)   .strip()
    config.stb_version = parser.get('iptv', 'STBVersion', raw=True).strip()
    config.conntype = parser.get('iptv', 'conntype', raw=True).strip()
    config.stbid = parser.get('iptv', 'STBID', raw=True).strip()
    config.template_name = parser.get('iptv', 'templateName', raw=True).strip()
    config.areaid = parser.get('iptv', 'areaId', raw=True).strip()
    config.usergroupid = parser.get('iptv', 'userGroupId', raw=True).strip()
    config.product_packageid = parser.get(
        'iptv', 'productPackageId', raw=True).strip()
    config.mac = parser.get('iptv', 'mac', raw=True).strip()
    config.user_field = parser.get('iptv', 'UserField', raw=True).strip()
    config.software_version = parser.get(
        'iptv', 'SoftwareVersion', raw=True).strip()
    config.is_smartstb = parser.get('iptv', 'IsSmartStb', raw=True).strip()
    config.desktopid = parser.get('iptv', 'desktopId', raw=True).strip()
    config.stbmarker = parser.get('iptv', 'stbmaker', raw=True).strip()
    config.xmpp_capability = parser.get(
        'iptv', 'XMPPCapability', raw=True).strip()
    config.chipid = parser.get('iptv', 'ChipID', raw=True).strip()
    config.vip = parser.get('iptv', 'VIP', raw=True).strip()

    repeat = dict(Counter(sections))

    for id, count in repeat.items():
        if count > 1:
            print(f'项 {id} 重复')

    user_number = 0
    for section in sections:
        id: int = int(section)
        number: str = parser.get(section, 'UserNumber').strip()
        user_number = int(number) if number.isdigit() else user_number + 1
        channel: ChannelConfig = ChannelConfig(
            id=id,
            name=parser.get(section, 'ChannelName').strip(),
            group=parser.get(section, 'ChannelGroup').strip(),
            user_number=str(user_number),
            logo=parser.get(section, 'Logo').strip(),
            epgid=parser.get(section, 'FromEPGID',fallback='UNKNOWN').strip(),
        )

        config.channels[id] = channel

    return UdpxyConfig(udpxy_url=udpxy_url, udpxy_protocal=udpxy_protocal), config
