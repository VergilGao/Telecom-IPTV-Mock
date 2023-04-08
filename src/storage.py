import sqlite3
from hashlib import md5
from datetime import datetime
from os import path
from json import loads as json_loads
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import SubElement
from xml.etree.ElementTree import ElementTree
from utils import pretty_xml


class Storage:
    def __init__(self, file_path: str):
        if not path.isfile(file_path):
            with sqlite3.connect(file_path) as connection:
                try:
                    c = connection.cursor()
                    c.executescript('''
CREATE TABLE overview(
    id              INTEGER         PRIMARY KEY AUTOINCREMENT,
    channel_id      INTEGER         NOT NULL,
    channel_name    VARCHAR(255)    NOT NULL,
    date            DATE            NOT NULL,
    hash            CHAR(32)        NOT NULL
);

CREATE TABLE programme (
    id              INTEGER         PRIMARY KEY AUTOINCREMENT,
    overview_id     INTEGER         NOT NULL,
    channel_id      INTEGER         NOT NULL,
    title           VARCHAR(255)    NOT NULL,
    start           DATETIME        NOT NULL,
    stop            DATETIME        NOT NULL,
    CONSTRAINT fk_overview
    FOREIGN KEY (overview_id)  
    REFERENCES overview(id)
);

CREATE UNIQUE INDEX unique_index_channel_date on overview (channel_id, date);
                    ''')

                    connection.commit()
                except Exception as exception:
                    connection.rollback()
                    raise exception
                finally:
                    c.close()

        self.__file = file_path

    def save(self, channel_id: int, channel_name: str, epg_date: datetime, json_str: str):
        hash = md5(json_str.encode('utf-8')).hexdigest()

        programs: list = json_loads(json_str).get('programs')
        if programs == None:
            return

        with sqlite3.connect(self.__file) as connection:
            try:
                c = connection.cursor()
                epg_date = epg_date.strftime('%Y-%m-%d')

                result = c.execute(
                    f'SELECT id,hash FROM overview WHERE date=\'{epg_date}\' AND channel_id=\'{channel_id}\'').fetchone()
                if result != None:
                    id, old_hash = result

                    if hash == old_hash:
                        print(f"频道{channel_name}时间为{epg_date}的节目单已缓存，跳过更新")
                        return

                    c.execute(
                        f'UPDATE overview SET hash=\'{hash}\' WHERE id=\'{id}\'')
                    c.execute(
                        f'DELETE FROM programme WHERE overview_id = \'{id}\'')
                else:
                    c.execute('INSERT INTO overview (channel_id, channel_name, date, hash) VALUES (?,?,?,?)', (
                        channel_id, channel_name, epg_date, hash))
                    connection.commit()
                    result = c.execute(
                        f'SELECT id FROM overview WHERE date=\'{epg_date}\' AND channel_id=\'{channel_id}\'').fetchone()
                    if result != None:
                        id = result[0]

                insert_list = []
                for program in programs:
                    try:
                        starttime = datetime.strptime(
                            program['starttime'], '%Y-%m-%d%H:%M:%S')
                        endtime = datetime.strptime(
                            program['endtime'], '%Y-%m-%d%H:%M:%S')
                        insert_list.append(
                            (id, channel_id, program['text'], starttime, endtime))
                    except Exception as exception:
                        print(f'存储{program}时出现异常，{exception}')

                c.executemany(
                    'INSERT INTO programme (overview_id, channel_id, title, start, stop) VALUES (?,?,?,?,?)', insert_list)
                connection.commit()
            except Exception as exception:
                connection.rollback()
                raise exception
            finally:
                c.close()

    def epg_generator(self, file: str,  start: datetime, end: datetime):
        start_date = start.strftime('%Y-%m-%d')
        end__date = end.strftime('%Y-%m-%d')

        channels: list[tuple[str, str]] = []
        programmes: list[tuple[str, str, datetime, datetime]] = []

        with sqlite3.connect(self.__file) as connection:
            try:
                c = connection.cursor()
                result = c.execute(
                    f'SELECT DISTINCT channel_id FROM overview WHERE date >= \'{start}\' and date < \'{end}\'').fetchall()

                if len(result) == 0:
                    pass

                lines = result

                for line in lines:
                    channel_id = line[0]

                    result = c.execute(
                        f'SELECT id,channel_name FROM overview WHERE date >= \'{start_date}\' and date < \'{end__date}\' and channel_id = \'{channel_id}\' order by date asc').fetchall()

                    if len(result) == 0:
                        pass

                    channel_name = result[len(result) - 1][1]
                    channel_id = f'{channel_id}@iptv'

                    channels.append((channel_id, channel_name))

                    channel_lines = result
                    for channel_line in channel_lines:
                        result = c.execute(
                            f'SELECT title,start,stop FROM programme WHERE overview_id = \'{channel_line[0]}\' order by start asc').fetchall()

                        if len(result) == 0:
                            pass

                        program_lines = result
                        for title, start, stop in program_lines:
                            start = datetime.strptime(
                                start, '%Y-%m-%d %H:%M:%S')
                            stop = datetime.strptime(stop, '%Y-%m-%d %H:%M:%S')
                            programmes.append((channel_id, title, start.strftime(
                                '%Y%m%d%H%M%S +0800'), stop.strftime('%Y%m%d%H%M%S  +0800')))  # 没有必要纠结什么设置时区之类的，直接写死 +0800就完了
            finally:
                c.close()

        root = Element('tv')
        root.attrib['generator-info-name'] = 'Telecom-IPTV-Mock'

        for channel_id, channel_name in channels:
            channel_element = SubElement(root, 'channel')
            channel_element.attrib['id'] = channel_id

            display_name_element = SubElement(channel_element, 'display-name')
            display_name_element.attrib['lang'] = 'zh'
            display_name_element.text = channel_name

        for channel_id, title, start, stop in programmes:
            program_element = SubElement(root, 'programme')
            program_element.attrib['start'] = start
            program_element.attrib['stop'] = stop
            program_element.attrib['channel'] = channel_id
            title_element = SubElement(program_element, 'title')
            title_element.attrib['lang'] = 'zh'
            title_element.text = title
            desc_element = SubElement(program_element, 'desc')
            desc_element.attrib['lang'] = 'zh'

        pretty_xml(root, '  ', '\n')
        tree = ElementTree(root)
        tree.write(file, encoding='utf-8', xml_declaration=True)
