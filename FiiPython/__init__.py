# FiiPython/__init__.py
"""
FiiPython - FII无人机仿真系统
==============================

一个用于解析FII文件、计算无人机运动状态并生成可视化视频的仿真系统。

主要模块：
- ReadFii: 解析XML格式的动作文件
- CalculateState: 计算无人机连续运动状态
- DrawDrone: 生成可视化帧并保存视频
- VideoSaver: 内存优化的视频保存工具

版本: 1.0.0
"""

__version__ = '1.0.0'
__author__ = 'FII Team'
__license__ = 'MIT'

# 导入子模块
from . import ReadFii
from . import CalculateState as CS
from . import DrawDrone
from . import VideoSaver
from . import utils

# 为了方便使用，导出主要函数
from .ReadFii import readFii
from .CalculateState import calculateState
from .DrawDrone import show, save_video, generate_frames
from .VideoSaver import VideoSaver

# 设置模块别名
ReadFii = ReadFii
CS = CS
DrawDrone = DrawDrone
VideoSaver = VideoSaver
utils = utils

__all__ = [
    'readFii',
    'calculateState',
    'show',
    'save_video',
    'generate_frames',
    'VideoSaver',
    'ReadFii',
    'CS',
    'DrawDrone',
    'utils',
]