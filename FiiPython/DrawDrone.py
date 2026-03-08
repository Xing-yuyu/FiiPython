# DrawDrone.py (坐标系修复版)
import cv2
import numpy as np
import os
import xmltodict
from .VideoSaver import VideoSaver
import gc
import math
from typing import List, Dict, Any, Optional, Tuple, Generator


def get_file(key_name, path='./'):
    """直接获取某个目录中名称包含key_mane的文件全名"""
    for i in os.listdir(path):
        if key_name in i:
            return path + i


def get_takeoff_pos(xml_file):
    if not os.path.exists(xml_file):
        print(f"文件不存在: {xml_file}")

    with open(xml_file, 'r', encoding='utf-8') as file:
        content = file.read()

    dict_data = xmltodict.parse(content)
    drone_nums = len(dict_data['GoertekGraphicXml']['Actions'])
    print(drone_nums)
    print(dict_data['GoertekGraphicXml']['ActionFlightPosX'])
    takeoff_pos_list = []
    for i in range(drone_nums):
        x, y = dict_data['GoertekGraphicXml']['ActionFlightPosX'][i]['@actionfX'], \
            dict_data['GoertekGraphicXml']['ActionFlightPosY'][i]['@actionfY']
        xx = int(x[x.index('s') + 1:])
        yy = int(y[y.index('s') + 1:])
        takeoff_pos_list.append([xx, yy])
    print(takeoff_pos_list)
    return takeoff_pos_list


def world_to_screen(x, y, size):
    """
    将世界坐标系转换为屏幕坐标系

    世界坐标系: 原点在左下角, x向右, y向上
    屏幕坐标系: 原点在左上角, x向右, y向下

    Args:
        x: 世界坐标x
        y: 世界坐标y
        size: 场地尺寸

    Returns:
        (screen_x, screen_y) 屏幕坐标
    """
    screen_x = int(x + 20)  # 保持x不变，加20作为边距
    screen_y = int(size - y + 20)  # y需要翻转：屏幕y = 场地尺寸 - 世界y + 边距
    return screen_x, screen_y


def drawDrone(state, frame, size=560, clarity=1):
    """绘制无人机（直接绘制为BGR格式供OpenCV显示）"""
    pos = state['pos']
    try:
        # 复制一份，避免修改原数据
        world_x = pos[0]
        world_y = pos[1]
        world_z = pos[2]
    except:
        print(pos)
        return -1

    # 世界坐标转屏幕坐标
    screen_x, screen_y = world_to_screen(world_x, world_y, size)

    # 获取灯光颜色（已经是RGB格式）
    body_rgb = state['light']['body']
    motor1_rgb = state['light']['motor1']
    motor2_rgb = state['light']['motor2']
    motor3_rgb = state['light']['motor3']
    motor4_rgb = state['light']['motor4']

    # 转换为BGR格式（因为cv2使用BGR）
    body_bgr = (body_rgb[2], body_rgb[1], body_rgb[0])
    motor1_bgr = (motor1_rgb[2], motor1_rgb[1], motor1_rgb[0])
    motor2_bgr = (motor2_rgb[2], motor2_rgb[1], motor2_rgb[0])
    motor3_bgr = (motor3_rgb[2], motor3_rgb[1], motor3_rgb[0])
    motor4_bgr = (motor4_rgb[2], motor4_rgb[1], motor4_rgb[0])

    #边框关键点
    k1_pos=(0,0)
    k2_pos=(2*(size+40)*clarity,0)
    k3_pos=(2*(size+40)*clarity,600)
    k4_pos=((size+40)*clarity,600)
    k5_pos=((size+40)*clarity,(size+40)*clarity)
    k6_pos=(0,(size+40)*clarity)
    k7_pos=((size+40)*clarity,0)
    k8_pos=((size+40)*clarity,300*clarity)
    k9_pos=(2*(size+40)*clarity,300*clarity)

    #绘制边框
    cv2.line(frame,k1_pos,k2_pos,(255,255,255),clarity)
    cv2.line(frame, k2_pos, k3_pos, (255, 255, 255),clarity)
    cv2.line(frame, k3_pos, k4_pos, (255,255, 255), clarity)
    cv2.line(frame, k5_pos, k6_pos, (255,255, 255), clarity)
    cv2.line(frame, k1_pos, k6_pos, (255,255, 255), clarity)
    cv2.line(frame, k7_pos,k4_pos,(255,255,255),clarity)
    cv2.line(frame, k8_pos,k9_pos,(255, 255,255), clarity)

    """俯视图部分"""
    # 计算四个马达的位置（相对于中心）
    motor_offset = 7 * clarity

    # 中心点
    center_x = screen_x * clarity
    center_y = screen_y * clarity

    # 四个马达的位置（顺时针顺序）
    # 马达1: 左上
    motor1_x = center_x - motor_offset
    motor1_y = center_y - motor_offset
    # 马达2: 右上
    motor2_x = center_x + motor_offset
    motor2_y = center_y - motor_offset
    # 马达3: 右下
    motor3_x = center_x + motor_offset
    motor3_y = center_y + motor_offset
    # 马达4: 左下
    motor4_x = center_x - motor_offset
    motor4_y = center_y + motor_offset

    # 绘制无人机轮廓（白色 - BGR格式）
    # 交叉线
    cv2.line(frame, (motor1_x, motor1_y), (motor3_x, motor3_y), (255, 255, 255), clarity)
    cv2.line(frame, (motor2_x, motor2_y), (motor4_x, motor4_y), (255, 255, 255), clarity)

    # 绘制四个马达的圆圈（白色边框）
    cv2.circle(frame, (motor1_x, motor1_y), 7*clarity, (255, 255, 255), clarity)
    cv2.circle(frame, (motor2_x, motor2_y), 7*clarity, (255, 255, 255), clarity)
    cv2.circle(frame, (motor3_x, motor3_y), 7*clarity, (255, 255, 255), clarity)
    cv2.circle(frame, (motor4_x, motor4_y), 7*clarity, (255, 255, 255), clarity)

    # 绘制机身（填充颜色 - BGR）
    if body_bgr != (0,0,0):
        cv2.circle(frame, (center_x, center_y), 5*clarity, body_bgr, -1)

    # 绘制马达（填充颜色 - BGR）
    if motor1_bgr != (0,0,0):
        cv2.circle(frame, (motor1_x, motor1_y), 2*clarity, motor1_bgr, -1)
    if motor2_bgr != (0,0,0):
        cv2.circle(frame, (motor2_x, motor2_y), 2*clarity, motor2_bgr, -1)
    if motor3_bgr != (0,0,0):
        cv2.circle(frame, (motor3_x, motor3_y), 2*clarity, motor3_bgr, -1)
    if motor4_bgr != (0,0,0):
        cv2.circle(frame, (motor4_x, motor4_y), 2*clarity, motor4_bgr, -1)


    """前视图部分"""
    center_x_f=int(clarity*(size+60+world_x))
    center_z_f=int(clarity*(275-world_z))

    cv2.line(frame,(center_x_f-14*clarity,center_z_f),(center_x_f+14*clarity,center_z_f),(255,255,255),clarity)

    if body_bgr != (0, 0, 0):
        cv2.circle(frame, (center_x_f, center_z_f),5*clarity,body_bgr,-1)
    if motor3_bgr != (0,0,0):
        cv2.circle(frame,(center_x_f+9*clarity,center_z_f),3*clarity,motor3_bgr,-1)
    if motor4_bgr != (0,0,0):
        cv2.circle(frame, (center_x_f-9*clarity,center_z_f),3*clarity,motor4_bgr,-1)

    """右视图部分"""
    center_y_r =int( clarity * (size + 60 + world_y))
    center_z_r = int(clarity * (575 - world_z))

    cv2.line(frame, (center_y_r - 14 * clarity, center_z_r), (center_y_r + 14 * clarity, center_z_r), (255, 255, 255), clarity)
    if body_bgr != (0, 0, 0):
        cv2.circle(frame, (center_y_r, center_z_r), 5 * clarity, body_bgr, -1)
    if motor2_bgr != (0,0,0):
        cv2.circle(frame, (center_y_r + 9 * clarity, center_z_r), 3 * clarity, motor2_bgr, -1)
    if motor3_bgr != (0,0,0):
        cv2.circle(frame, (center_y_r - 9 * clarity, center_z_r), 3 * clarity, motor3_bgr, -1)

def generate_frames(states_list, size=560, clarity=1, target_fps=None, output_color_mode='BGR', max_memory_mb=1024):
    """
    生成帧数据生成器 - 核心函数，根据目标fps从状态中采样

    Args:
        states_list: 无人机状态列表
        size: 场地尺寸
        clarity: 清晰度
        target_fps: 目标帧率，None表示使用所有帧
        output_color_mode: 输出颜色模式 'RGB' 或 'BGR'
        max_memory_mb: 最大内存使用(MB)，用于分批处理

    Yields:
        生成的帧
    """
    # 计算总帧数
    states_lengths = [len(i) for i in states_list]
    total_original_frames = max(states_lengths)

    # 确定要采样的帧索引
    if target_fps:
        # 原始数据是1000fps
        sample_interval = 1000 / target_fps
        frame_indices = [int(i * sample_interval) for i in range(int(total_original_frames / sample_interval) + 1)]
        frame_indices = [i for i in frame_indices if i < total_original_frames]
        print(f"采样: 从 {total_original_frames} 帧 (1000fps) 采样到 {len(frame_indices)} 帧 ({target_fps}fps)")
    else:
        frame_indices = list(range(total_original_frames))
        print(f"使用全部 {total_original_frames} 帧")

    total_output_frames = len(frame_indices)

    # 预估每帧内存大小
    frame_height = 600 * clarity
    frame_width = 2*(size + 40) * clarity
    frame_size_bytes = frame_height * frame_width * 3
    frames_per_batch = max(1, int((max_memory_mb * 1024 * 1024) / frame_size_bytes))

    print(f"每帧尺寸: {frame_width}x{frame_height}, 每帧约 {frame_size_bytes / (1024 * 1024):.2f} MB")
    print(f"每批处理 {frames_per_batch} 帧")

    # 分批生成帧
    for batch_start in range(0, total_output_frames, frames_per_batch):
        batch_end = min(batch_start + frames_per_batch, total_output_frames)
        batch_indices = frame_indices[batch_start:batch_end]

        # 生成这一批的帧
        for frame_idx in batch_indices:
            # 创建新帧（初始化为黑色，BGR格式）
            frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)

            # 绘制所有无人机在这一帧的状态
            for state_dict in states_list:
                state_num_max = list(state_dict.keys())[-1]
                try:
                    # 如果当前帧索引存在
                    if frame_idx in state_dict:
                        drawDrone(state_dict[frame_idx], frame, size, clarity)
                    else:
                        # 如果当前帧不存在，使用最后一帧
                        drawDrone(state_dict[state_num_max], frame, size, clarity)
                except Exception as e:
                    print(f"绘制错误: {e}, frame_idx={frame_idx}")

            # 如果需要RGB格式输出
            if output_color_mode.upper() == 'RGB':
                # BGR -> RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                yield frame_rgb
            else:
                # 直接输出BGR
                yield frame

        # 每批处理后强制垃圾回收
        gc.collect()
        print(f"已生成 {batch_end}/{total_output_frames} 帧", end='\r')


def show_optimized(states_list, size=560, show_fps=60, simulate=True, save=True,
                   save_as='video.mp4', video_fps=60, clarity=1, max_memory_mb=1024):
    """
    优化的显示函数 - 分离保存和显示模式，统一帧生成逻辑

    Args:
        states_list: 无人机状态列表
        size: 场地尺寸
        show_fps: 显示帧率
        simulate: 是否窗口模拟
        save: 是否保存
        save_as: 保存文件名
        video_fps: 视频帧率
        clarity: 清晰度
        max_memory_mb: 最大内存使用(MB)
    """
    print(f"\n开始处理: 显示帧率={show_fps}fps, 视频帧率={video_fps}fps")

    # 获取音频文件
    audio_file = get_file('.mp3', './动作组/')
    if audio_file:
        print(f"找到音频文件: {audio_file}")

    if save and simulate:
        # 同时保存和显示 - 需要生成两次帧
        print("同时保存和显示模式...")

        # 先保存视频
        print("生成视频帧...")
        # 注意：保存视频时，生成BGR格式，因为VideoSaver会处理颜色
        video_generator = generate_frames(states_list, size, clarity, video_fps, 'BGR', max_memory_mb)

        # 保存视频 - VideoSaver接收BGR格式
        saver = VideoSaver(video_fps)
        total_frames = len([i for i in range(0, max(len(s) for s in states_list), int(1000 / video_fps))])
        saver.save_video_from_generator(
            video_generator,
            save_as,
            total_frames=total_frames,
            audio_path=audio_file,
            frame_color_mode='BGR'  # 告诉VideoSaver输入是BGR格式
        )

        # 再生成用于显示的帧
        print("\n准备显示...")
        # 显示时也需要BGR格式（cv2.imshow需要）
        show_generator = generate_frames(states_list, size, clarity, show_fps, 'BGR', max_memory_mb)

        # 播放
        print("\n开始播放，按 'q' 退出")
        frame_count = 0
        for frame in show_generator:
            # frame已经是BGR格式，直接显示
            cv2.imshow('Drone Simulation', frame)
            frame_count += 1
            print(f"播放帧 {frame_count}", end='\r')

            if cv2.waitKey(int(1000 / show_fps)) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()

    elif save:
        # 纯保存模式
        print("纯保存模式...")
        video_generator = generate_frames(states_list, size, clarity, video_fps, 'BGR', max_memory_mb)
        saver = VideoSaver(video_fps)
        total_frames = len([i for i in range(0, max(len(s) for s in states_list), int(1000 / video_fps))])
        saver.save_video_from_generator(
            video_generator,
            save_as,
            total_frames=total_frames,
            audio_path=audio_file,
            frame_color_mode='BGR'
        )

    elif simulate:
        # 纯显示模式
        print("纯显示模式...")
        show_generator = generate_frames(states_list, size, clarity, show_fps, 'BGR', max_memory_mb)

        print("\n开始播放，按 'q' 退出")
        frame_count = 0
        for frame in show_generator:
            cv2.imshow('Drone Simulation', frame)
            frame_count += 1
            print(f"播放帧 {frame_count}", end='\r')

            if cv2.waitKey(int(1000 / show_fps)) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()


def show(states_list, size=560, show_fps=60, simulate=True, save=True,
         save_as='video.mp4', video_fps=60, clarity=1, max_memory_mb=1024):
    """
    兼容原接口的显示函数
    """
    show_optimized(states_list, size, show_fps, simulate, save, save_as, video_fps, clarity, max_memory_mb)


def save_video(frames, video_name='video.mp4', fps=1000):
    """
    兼容原接口的保存函数
    """
    print("警告: 使用旧的save_video函数，建议使用新的优化版本")
    saver = VideoSaver(fps)
    audio_file = get_file('.mp3', './动作组/')
    print("\n保存带音频视频...")
    saver.save_video(frames, video_name, audio_file)
    print("\n完成！")