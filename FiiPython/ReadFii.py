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


def read_dict_xml(dict_node, final_dict, cnt_time):  # 递归读这个飞机的xml???
    try:
        ###print(dict_node.keys())
        ###print(dict_node['@type'])
        # print(dict_node)
        block_type = dict_node['@type']

        # 确保当前时间戳存在
        final_dict = ensure_time_exists(final_dict, cnt_time)

        if isinstance(dict_node, list):
            print(f"跳过同级元素列表，长度 {len(dict_node)}")
            return final_dict, cnt_time

            # 确保 dict_node 是字典
        if not isinstance(dict_node, dict):
            return final_dict, cnt_time

        if block_type == 'block_inittime':
            # print(dict_node['field'][0]['#text'])
            time_str = dict_node['field'][0]['#text']
            minutes, seconds = map(int, time_str.split(':'))
            cnt_time = minutes * 60 * 1000 + seconds * 1000
            ###print(f'{cnt_time}ms')
            final_dict = ensure_time_exists(final_dict, cnt_time)
            #print(final_dict, cnt_time)
            # 处理statement中的block
            if 'statement' in dict_node and dict_node['statement'] and 'block' in dict_node['statement']:
                final_dict, cnt_time = read_dict_xml(dict_node['statement']['block'], final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'block_delay':  # 太好了终于是delay
            unit_of_time = dict_node['field'][0]['#text']  # 为str 0=ms 1=s 2=minute
            value = int(dict_node['field'][1]['#text'])
            ###print(unit_of_time,value)

            time_multipliers = {'0': 1, '1': 1000, '2': 60000}
            cnt_time += value * time_multipliers.get(unit_of_time, 1)

            final_dict = ensure_time_exists(final_dict, cnt_time)
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_TakeOff2':  # 芜湖起飞  {'TakeOff': height}
            height = int(dict_node['field']['#text'])
            # print(height)
            final_dict[cnt_time]['TakeOff'] = height
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        # 2代灯光 - 全身灯光 (机身+马达) 使用 All 前缀
        elif block_type == 'Goertek_LEDBreathALL2':  # 全身呼吸灯 {'AllBreath': {'color':(r,g,b),'time1':time1,'time2':time2,'brightness':百分数化小数}}
            color = hex_to_rgb(dict_node['field'][1]['#text'])
            time1 = int(dict_node['field'][0]['#text'])
            time2 = int(dict_node['field'][3]['#text'])
            brightness = float(dict_node['field'][2]['#text'])
            final_dict[cnt_time]['AllBreath'] = {'color': color, 'time1': time1, 'time2': time2,
                                                 'brightness': brightness}
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_LEDTurnOnAllSingleColor2':  # 全身灯全亮 {'AllOn': (r,g,b)}
            color = hex_to_rgb(dict_node['field']['#text'])
            final_dict[cnt_time]['AllOn'] = color
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_LEDTurnOffAll2':  # 全身灯全灭 {'AllOff': 0}
            final_dict[cnt_time]['AllOff'] = 0
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_LEDBlinkALL2':  # 全身闪烁灯 {'AllBlink': {'color':(r,g,b),'brightness':brightness,'dur':dur,'delay':delay}}
            color = hex_to_rgb(dict_node['field'][0]['#text'])
            brightness = float(dict_node['field'][1]['#text'])
            dur = int(dict_node['field'][2]['#text'])
            delay = int(dict_node['field'][3]['#text'])
            final_dict[cnt_time]['AllBlink'] = {'color': color, 'brightness': brightness, 'dur': dur, 'delay': delay}
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        # 3代灯光 - 机身灯光 (不含马达)
        elif block_type == 'Goertek_LEDBreathALL3':  # 机身呼吸灯 {'BodyBreath': {'color':(r,g,b),'time1':time1,'time2':time2,'brightness':百分数化小数}}
            color = hex_to_rgb(dict_node['field'][1]['#text'])
            time1 = int(dict_node['field'][0]['#text'])
            time2 = int(dict_node['field'][3]['#text'])
            brightness = float(dict_node['field'][2]['#text'])
            final_dict[cnt_time]['BodyBreath'] = {'color': color, 'time1': time1, 'time2': time2,
                                                  'brightness': brightness}
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_LEDTurnOnAllSingleColor3':  # 机身灯全亮 {'BodyOn': (r,g,b)}
            color = hex_to_rgb(dict_node['field']['#text'])
            final_dict[cnt_time]['BodyOn'] = color
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_LEDTurnOffAll3':  # 机身灯全灭 {'BodyOff': 0}
            final_dict[cnt_time]['BodyOff'] = 0
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_LEDBlinkALL3':  # 机身闪烁灯 {'BodyBlink': {'color':(r,g,b),'brightness':brightness,'dur':dur,'delay':delay}}
            color = hex_to_rgb(dict_node['field'][0]['#text'])
            brightness = float(dict_node['field'][1]['#text']) / 100
            dur = int(dict_node['field'][2]['#text'])
            delay = int(dict_node['field'][3]['#text'])
            final_dict[cnt_time]['BodyBlink'] = {'color': color, 'brightness': brightness, 'dur': dur, 'delay': delay}
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        # 4代灯光 - 马达灯光
        elif block_type == 'Goertek_LEDTurnOnAllSingleColor4':  # 指定马达灯全亮 {'MotorOn': {'motor':马达编号, 'color':(r,g,b)}}
            motor = int(dict_node['field'][0]['#text'])  # 马达编号：0-全亮 1~4-1~4号马达
            color = hex_to_rgb(dict_node['field'][1]['#text'])
            final_dict[cnt_time]['MotorOn'] = {'motor': motor, 'color': color}
            # 添加注释说明马达编号含义
            motor_desc = "0-全亮" if motor == 0 else f"{motor}号马达"
            #print(f"MotorOn: 马达 {motor_desc}, 颜色 {color}")
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_LEDTurnOffAll4':  # 指定马达关灯 {'MotorOff': motor}
            motor = int(dict_node['field']['#text'])  # 马达编号：0-全亮 1~4-1~4号马达
            final_dict[cnt_time]['MotorOff'] = motor
            # 添加注释说明马达编号含义
            motor_desc = "0-全亮" if motor == 0 else f"{motor}号马达"
            #print(f"MotorOff: 马达 {motor_desc}")
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_LEDBlinkALL4':  # 指定马达闪烁灯 {'MotorBlink': {'motor':马达编号, 'color':(r,g,b), 'brightness':brightness, 'dur':dur, 'delay':delay}}
            motor = int(dict_node['field'][0]['#text'])  # 马达编号：0-全亮 1~4-1~4号马达
            color = hex_to_rgb(dict_node['field'][1]['#text'])
            brightness = float(dict_node['field'][2]['#text'])
            dur = int(dict_node['field'][3]['#text'])
            delay = int(dict_node['field'][4]['#text'])
            final_dict[cnt_time]['MotorBlink'] = {'motor': motor, 'color': color, 'brightness': brightness, 'dur': dur,
                                                  'delay': delay}
            # 添加注释说明马达编号含义
            motor_desc = "0-全亮" if motor == 0 else f"{motor}号马达"
            #print(f"MotorBlink: 马达 {motor_desc}, 颜色 {color}")
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_LEDBreathALL4':  # 指定马达呼吸灯 {'MotorBreath': {'motor':马达编号, 'color':(r,g,b), 'time1':time1, 'time2':time2, 'brightness':brightness}}
            motor = int(dict_node['field'][0]['#text'])  # 马达编号：0-全亮 1~4-1~4号马达
            time1 = int(dict_node['field'][1]['#text'])
            color = hex_to_rgb(dict_node['field'][2]['#text'])
            brightness = float(dict_node['field'][3]['#text'])
            time2 = int(dict_node['field'][4]['#text'])
            final_dict[cnt_time]['MotorBreath'] = {'motor': motor, 'color': color, 'time1': time1, 'time2': time2,
                                                   'brightness': brightness}
            # 添加注释说明马达编号含义
            motor_desc = "0-全亮" if motor == 0 else f"{motor}号马达"
            #print(f"MotorBreath: 马达 {motor_desc}, 颜色 {color}")
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_LEDHorseALL4':  # 跑马灯 {'MotorHorse': {'colors':[color1,color2,color3,color4], 'clock':clock, 'delay':delay}}
            color1 = hex_to_rgb(dict_node['field'][0]['#text'])
            color2 = hex_to_rgb(dict_node['field'][1]['#text'])
            color3 = hex_to_rgb(dict_node['field'][2]['#text'])
            color4 = hex_to_rgb(dict_node['field'][3]['#text'])
            clock = dict_node['field'][4]['#text'] == 'True'
            delay = int(dict_node['field'][5]['#text'])
            final_dict[cnt_time]['MotorHorse'] = {'colors': [color1, color2, color3, color4], 'clock': clock,
                                                  'delay': delay}
            #print(f"MotorHorse: 颜色 {color1}, {color2}, {color3}, {color4}")
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_HorizontalSpeed':  # 水平速度加速度 {'XYSpeed': [v,a]}
            v = int(dict_node['field'][0]['#text'])
            a = int(dict_node['field'][1]['#text'])
            final_dict[cnt_time]['XYSpeed'] = [v, a]
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_VerticalSpeed':  # 竖直速度加速度 {'ZSpeed': [v,a]}
            v = int(dict_node['field'][0]['#text'])
            a = int(dict_node['field'][1]['#text'])
            final_dict[cnt_time]['ZSpeed'] = [v, a]
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_Move':  # 相对移动 {'Move': [x,y,z]}
            x = int(float(dict_node['field'][0]['#text']))  # 先转float再转int，支持负数
            y = int(float(dict_node['field'][1]['#text']))
            z = int(float(dict_node['field'][2]['#text']))
            final_dict[cnt_time]['Move'] = [x, y, z]
            print(f"相对移动: ({x}, {y}, {z})")
            print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_MoveToCoord2':  # 移动到坐标 {'MoveTo': [x,y,z]}
            x = int(float(dict_node['field'][0]['#text']))
            y = int(float(dict_node['field'][1]['#text']))
            z = int(float(dict_node['field'][2]['#text']))
            final_dict[cnt_time]['MoveTo'] = [x, y, z]
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_Land':  # 降落 {'Land': 0}
            final_dict[cnt_time]['Land'] = 0
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        # 其他块类型
        elif block_type == 'Goertek_Point2':  # 定义点 {'Point': {'name':name, 'coord':[x,y,z]}}
            name = dict_node['field'][0]['#text']
            x = int(dict_node['field'][1]['#text'])
            y = int(dict_node['field'][2]['#text'])
            z = int(dict_node['field'][3]['#text'])
            final_dict[cnt_time]['Point'] = {'name': name, 'coord': [x, y, z]}
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_AngularVelocity':  # 角速度 {'AngularVelocity': w}
            w = int(dict_node['field']['#text'])
            final_dict[cnt_time]['AngularVelocity'] = w
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_TurnTo':  # 转向到角度 {'TurnTo': {'direction':direction, 'angle':angle}}
            direction = dict_node['field'][0]['#text']
            angle = int(dict_node['field'][1]['#text'])
            final_dict[cnt_time]['TurnTo'] = {'direction': direction, 'angle': angle}
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_Turn':  # 转向 {'Turn': {'direction':direction, 'angle':angle}}
            direction = dict_node['field'][0]['#text']
            angle = int(dict_node['field'][1]['#text'])
            final_dict[cnt_time]['Turn'] = {'direction': direction, 'angle': angle}
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_HighSpeedTranslate':  # 高速平移 {'HighSpeedTranslate': {'axis':axis, 'distance':d}}
            axis = dict_node['field'][0]['#text']
            distance = int(dict_node['field'][1]['#text'])
            final_dict[cnt_time]['HighSpeedTranslate'] = {'axis': axis, 'distance': distance}
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_SimpleHarmonicMotio':  # 简谐运动 {'SimpleHarmonicMotion': {'axis':axis, 'amplitude':amplitude}}
            axis = dict_node['field'][0]['#text']
            amplitude = int(dict_node['field'][1]['#text'])
            final_dict[cnt_time]['SimpleHarmonicMotion'] = {'axis': axis, 'amplitude': amplitude}
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        elif block_type == 'Goertek_Lock':  # 上锁 {'Lock': 0}
            final_dict[cnt_time]['Lock'] = 0
            #print(final_dict, cnt_time)
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)




        elif block_type == 'controls_repeat':  # 循环 - 直接展开成正常块

            times = int(dict_node['field']['#text'])

            print(f"展开循环 {times} 次")

            # 处理循环内的语句，获取完整的循环体内容（包括next链）

            if 'statement' in dict_node and dict_node['statement'] and 'block' in dict_node['statement']:

                # 临时存储循环体

                loop_body_dict = {}

                loop_body_time = 0

                # 递归读取statement中的整个block链

                loop_body_dict, loop_body_time = read_dict_xml(

                    dict_node['statement']['block'],

                    loop_body_dict,

                    loop_body_time

                )

                # 去除循环体内的空时间戳（但保留有动作的时间戳）

                loop_body_dict = remove_empty_timestamps(loop_body_dict)

                # 按时间戳排序获取循环体的动作序列

                sorted_times = sorted(loop_body_dict.keys())

                if sorted_times:

                    print(f"循环体内容 (相对时间):")

                    for t in sorted_times:
                        print(f"  {t}ms: {loop_body_dict[t]}")

                    # 循环体的总时长（最后一个动作的时间 + ？）

                    # 注意：最后一个动作之后可能还有延时，但延时不会产生动作

                    # 所以循环体的总时长应该是 loop_body_time（最后一个块处理完的时间）

                    total_loop_duration = loop_body_time

                    print(f"循环体总时长: {total_loop_duration}ms")

                    # 保存当前时间，用于循环内时间戳计算

                    base_time = cnt_time

                    # 展开循环times次

                    for i in range(times):

                        # 对循环体中的每个动作，复制并调整时间戳

                        for t in sorted_times:

                            # 新时间戳 = 基础时间 + 循环次数 * 循环体总时长 + 动作的相对时间

                            new_time = base_time + i * total_loop_duration + t

                            # 确保该时间戳有字典

                            final_dict = ensure_time_exists(final_dict, new_time)

                            # 复制动作

                            for key, value in loop_body_dict[t].items():

                                if key in final_dict[new_time]:

                                    print(f"错误: 时间戳 {new_time}ms 已有 {key} 动作")

                                else:

                                    final_dict[new_time][key] = value

                            print(f"循环展开 {i + 1}/{times}: {new_time}ms -> {final_dict[new_time]}")

                    # 更新cnt_time到循环结束后的时间

                    cnt_time = base_time + times * total_loop_duration

                    print(f"循环结束，当前时间: {cnt_time}ms")

            # 处理next中的block

            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)


        elif block_type in ['Goertek_Start','Goertek_UnLock','Goertek_Lock']:
            print('Fuck Goertek')
            # 处理next中的block
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        else:
            #print(f"未知类型: {block_type}")
            # 对于未知类型，仍然尝试处理next和statement
            if 'statement' in dict_node and dict_node['statement'] and 'block' in dict_node['statement']:
                final_dict, cnt_time = read_dict_xml(dict_node['statement']['block'], final_dict, cnt_time)
            if 'next' in dict_node and dict_node['next'] and 'block' in dict_node['next']:
                final_dict, cnt_time = read_dict_xml(dict_node['next']['block'], final_dict, cnt_time)

        return final_dict, cnt_time

    except Exception as e:
        print(f"错误: {e}")
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