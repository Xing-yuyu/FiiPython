"""工具函数模块"""

import os
from typing import Optional


def get_file(key_name: str, path: str = './') -> Optional[str]:
    """
    获取目录中包含关键字的文件完整路径

    Args:
        key_name: 文件名中包含的关键字
        path: 搜索路径

    Returns:
        匹配的文件完整路径，如果未找到则返回None
    """
    if not os.path.exists(path):
        return None

    for filename in os.listdir(path):
        if key_name in filename:
            return os.path.join(path, filename)
    return None


def hex_to_rgb(hex_color: str) -> tuple:
    """
    将十六进制颜色代码转换为RGB元组

    Args:
        hex_color: 十六进制颜色代码，如 '#FF0000'

    Returns:
        (r, g, b) 颜色元组
    """
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b)


def ensure_directory(path: str) -> None:
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(path):
        os.makedirs(path)