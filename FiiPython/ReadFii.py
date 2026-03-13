# 这个函数文件把xml读出来,然后换成dict,然后通过递归去读取行为(起飞移动灯光),接着以时间戳的形式返回,估计是{1000:{'move':[x,y,z],'AllOn':(r,g,b)},5000:{'TakeOff':height}}的形式吧


try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import xmltodict
import os
import json

"""def print_dict_xml(dict):
    print(dict.keys())
    print(dict['@type'])
    print_dict_xml(dict['next']['block'])"""

def get_file(key_name,path='./'):
    """直接获取某个目录中名称包含key_mane的文件全名"""
    for i in os.listdir(path):
        if key_name in i:
            return path+i

def hex_to_rgb(hex_color):
    # 去掉颜色代码前面的#
    hex_color = hex_color.lstrip('#')
    # 将16进制颜色代码转换为RGB格式
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b)


def ensure_time_exists(final_dict, cnt_time):
    """确保指定时间戳的字典存在"""
    if cnt_time not in final_dict:
        final_dict[cnt_time] = {}
    return final_dict


def remove_empty_timestamps(final_dict):
    """去除空的时间戳"""
    return {time: actions for time, actions in final_dict.items() if actions}


# ReadFii.py (极简修复版)

def read_dict_xml(dict_node, final_dict, cnt_time):
    """
    递归读取XML字典节点
    修复：处理dict_node可能是列表的情况
    """
    try:
        # 处理 dict_node 是列表的情况
        if isinstance(dict_node, list):
            # 如果是列表，遍历每个元素
            for node in dict_node:
                final_dict, cnt_time = read_dict_xml(node, final_dict, cnt_time)
            return final_dict, cnt_time

        # 确保 dict_node 是字典
        if not isinstance(dict_node, dict):
            print(f"警告: dict_node 不是字典: {type(dict_node)}")
            return final_dict, cnt_time

        # 获取block类型
        block_type = dict_node.get('@type')
        if not block_type:
            # 如果没有@type，尝试处理next或statement
            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)
            if 'statement' in dict_node and dict_node['statement']:
                stmt_block = dict_node['statement'].get('block')
                if stmt_block:
                    final_dict, cnt_time = read_dict_xml(stmt_block, final_dict, cnt_time)
            return final_dict, cnt_time

        # 确保当前时间戳存在
        final_dict = ensure_time_exists(final_dict, cnt_time)

        # 根据block_type处理不同指令
        if block_type == 'block_inittime':
            # 处理初始化时间
            fields = dict_node.get('field', [])
            if fields and isinstance(fields, list) and len(fields) > 0:
                time_str = fields[0].get('#text', '0:00')
                minutes, seconds = map(int, time_str.split(':'))
                cnt_time = minutes * 60 * 1000 + seconds * 1000
                final_dict = ensure_time_exists(final_dict, cnt_time)

            # 处理statement
            if 'statement' in dict_node and dict_node['statement']:
                stmt_block = dict_node['statement'].get('block')
                if stmt_block:
                    final_dict, cnt_time = read_dict_xml(stmt_block, final_dict, cnt_time)

            # 处理next
            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        elif block_type == 'block_delay':
            # 处理延时
            fields = dict_node.get('field', [])
            if fields and isinstance(fields, list) and len(fields) >= 2:
                unit = fields[0].get('#text', '0')
                value = int(fields[1].get('#text', '0'))

                time_multipliers = {'0': 1, '1': 1000, '2': 60000}
                cnt_time += value * time_multipliers.get(unit, 1)
                final_dict = ensure_time_exists(final_dict, cnt_time)

            # 处理next
            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        elif block_type == 'Goertek_TakeOff2':
            # 起飞
            field = dict_node.get('field', {})
            if isinstance(field, dict):
                height = int(field.get('#text', 0))
            elif isinstance(field, list) and len(field) > 0:
                height = int(field[0].get('#text', 0))
            else:
                height = 0
            final_dict[cnt_time]['TakeOff'] = height

            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        elif block_type == 'Goertek_Move':
            # 相对移动
            fields = dict_node.get('field', [])
            if fields and isinstance(fields, list) and len(fields) >= 3:
                x = int(float(fields[0].get('#text', '0')))
                y = int(float(fields[1].get('#text', '0')))
                z = int(float(fields[2].get('#text', '0')))
                final_dict[cnt_time]['Move'] = [x, y, z]
                print(f"相对移动: ({x}, {y}, {z})")

            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        elif block_type == 'Goertek_MoveToCoord2':
            # 绝对移动
            fields = dict_node.get('field', [])
            if fields and isinstance(fields, list) and len(fields) >= 3:
                x = int(float(fields[0].get('#text', '0')))
                y = int(float(fields[1].get('#text', '0')))
                z = int(float(fields[2].get('#text', '0')))
                final_dict[cnt_time]['MoveTo'] = [x, y, z]

            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        elif block_type == 'Goertek_Land':
            # 降落
            final_dict[cnt_time]['Land'] = 0
            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        elif block_type == 'Goertek_HorizontalSpeed':
            # 水平速度
            fields = dict_node.get('field', [])
            if fields and isinstance(fields, list) and len(fields) >= 2:
                v = int(fields[0].get('#text', '100'))
                a = int(fields[1].get('#text', '100'))
                final_dict[cnt_time]['XYSpeed'] = [v, a]

            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        elif block_type == 'Goertek_VerticalSpeed':
            # 垂直速度
            fields = dict_node.get('field', [])
            if fields and isinstance(fields, list) and len(fields) >= 2:
                v = int(fields[0].get('#text', '100'))
                a = int(fields[1].get('#text', '100'))
                final_dict[cnt_time]['ZSpeed'] = [v, a]

            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        elif block_type == 'controls_repeat':
            # 循环展开
            field = dict_node.get('field', {})
            if isinstance(field, dict):
                times = int(field.get('#text', '1'))
            elif isinstance(field, list) and len(field) > 0:
                times = int(field[0].get('#text', '1'))
            else:
                times = 1

            print(f"展开循环 {times} 次")

            if 'statement' in dict_node and dict_node['statement']:
                stmt_block = dict_node['statement'].get('block')
                if stmt_block:
                    # 临时存储循环体
                    loop_body_dict = {}
                    loop_body_time = 0
                    loop_body_dict, loop_body_time = read_dict_xml(stmt_block, loop_body_dict, loop_body_time)

                    # 去除空时间戳
                    loop_body_dict = remove_empty_timestamps(loop_body_dict)

                    if loop_body_dict:
                        sorted_times = sorted(loop_body_dict.keys())
                        total_loop_duration = loop_body_time

                        # 展开循环
                        base_time = cnt_time
                        for i in range(times):
                            for t in sorted_times:
                                new_time = base_time + i * total_loop_duration + t
                                final_dict = ensure_time_exists(final_dict, new_time)
                                for key, value in loop_body_dict[t].items():
                                    final_dict[new_time][key] = value

                        cnt_time = base_time + times * total_loop_duration

            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        elif block_type in ['Goertek_Start', 'Goertek_UnLock', 'Goertek_Lock']:
            print('跳过指令:', block_type)
            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        else:
            # 未知类型，尝试处理next和statement
            if 'statement' in dict_node and dict_node['statement']:
                stmt_block = dict_node['statement'].get('block')
                if stmt_block:
                    final_dict, cnt_time = read_dict_xml(stmt_block, final_dict, cnt_time)
            if 'next' in dict_node and dict_node['next']:
                next_block = dict_node['next'].get('block')
                if next_block:
                    final_dict, cnt_time = read_dict_xml(next_block, final_dict, cnt_time)

        return final_dict, cnt_time

    except Exception as e:
        print(f"解析错误: {e}")
        import traceback
        traceback.print_exc()
        return final_dict, cnt_time

def read_fii_xml():
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import xml.etree.ElementTree as ET

    xml_file = get_file('.fii')
    if not os.path.exists(xml_file):
        print(f"文件不存在: {xml_file}")

    with open(xml_file, 'r', encoding='utf-8') as file:
        content = file.read()
    dict_data = xmltodict.parse(content)
    if dict_data['GoertekGraphicXml']['AreaL']['@AreaL'] == '600':
        size = 560
    elif dict_data['GoertekGraphicXml']['AreaL']['@AreaL'] == '400':
        size = 400
    elif dict_data['GoertekGraphicXml']['AreaL']['@AreaL'] == '115':
        size = 80
    elif dict_data['GoertekGraphicXml']['AreaL']['@AreaL'] == '73':
        size = 40
    else:
        size = 560
    print(size)
    drone_nums = len(dict_data['GoertekGraphicXml']['Actions'])
    print(drone_nums)

    takeoff_pos_list = []
    for i in range(drone_nums):
        x, y = dict_data['GoertekGraphicXml']['ActionFlightPosX'][i]['@actionfX'], \
        dict_data['GoertekGraphicXml']['ActionFlightPosY'][i]['@actionfY']
        xx = int(x[x.index('s') + 1:])
        yy = int(y[y.index('s') + 1:])
        takeoff_pos_list.append([xx, yy])
    print(takeoff_pos_list)

    return size,takeoff_pos_list

def readFii(xml_file='./'):
    """留空默认为./具体到项目目录就行"""
    size,takeoff_pos_list= read_fii_xml()
    final_dict_list=[]
    try:
        os.mkdir('final_dict_list')
    except:
        pass

    for i in range(len(takeoff_pos_list)):
        final_dict = {}
        cnt_time = 0
        xml_file=get_file('.xml',f'./动作组/动作组{i+1}/')
        if not os.path.exists(xml_file):
            print(f"文件不存在: {xml_file}")
            return final_dict

        with open(xml_file, 'r', encoding='utf-8') as file:
            content = file.read()

        dict_data = xmltodict.parse(content)
        # print(dict_data)
        # print(dict_data['xml']['block'])
        final_dict, cnt_time = read_dict_xml(dict_data['xml']['block'], final_dict, cnt_time)

        # 去除空的时间戳
        final_dict = remove_empty_timestamps(final_dict)

        print("\n最终结果 (已去除空时间戳):")
        #print(final_dict)
        final_dict_list.append(final_dict)
        # 按时间戳排序打印
        """for time in sorted(final_dict.keys()):
            print(f"{time}ms: {final_dict[time]}")"""
        print(f"最终时间: {cnt_time}ms")
        with open(f'./final_dict_list/final_dict_drone{i+1}.json', "w", encoding='utf-8') as f:  ## 设置'utf-8'编码
            f.write(json.dumps(final_dict, ensure_ascii=False))

    return size,takeoff_pos_list,final_dict_list


if __name__ == '__main__':
    readFii('./')