from Crypto.Cipher import DES
from hashlib import md5

def pretty_xml(element, indent, newline, level=0):
    # 判断element是否有子元素
    if element:
        # 如果element的text没有内容
        if element.text == None or element.text.isspace():
            element.text = newline + indent * (level + 1)
        else:
            element.text = newline + indent * \
                (level + 1) + element.text.strip() + \
                newline + indent * (level + 1)
    temp = list(element)  # 将elemnt转成list
    for subelement in temp:
        # 如果不是list的最后一个元素，说明下一个行是同级别元素的起始，缩进应一致
        if temp.index(subelement) < (len(temp) - 1):
            subelement.tail = newline + indent * (level + 1)
        else:  # 如果是list的最后一个元素， 说明下一行是母元素的结束，缩进应该少一个
            subelement.tail = newline + indent * level
        # 对子元素进行递归操作
        pretty_xml(subelement, indent, newline, level=level + 1)

def __pkcs7(s: str) -> str:
    bs: int = DES.block_size
    return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)


def getAuthenticator(userid: str, password: str, stbid: str, mac: str, encry_token: str, salt: str) -> str:
    salty: bytes = (password + salt).encode('ascii')
    payload: bytes = __pkcs7("99999${token}${user}${stb}$127.0.0.1${mac}$$CTC".format(
        token=encry_token,
        user=userid,
        stb=stbid,
        mac=mac
    )).encode('ascii')

    key: bytes = bytes(md5(salty).hexdigest()[:8], encoding='ascii')
    return (DES.new(key, DES.MODE_ECB).encrypt(payload)).hex().upper()