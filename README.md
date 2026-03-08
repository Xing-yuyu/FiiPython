# FiiPython - FII无人机仿真系统

[![PyPI version](https://img.shields.io/pypi/v/FiiPython.svg)](https://pypi.org/project/FiiPython/)
[![Python versions](https://img.shields.io/pypi/pyversions/FiiPython.svg)](https://pypi.org/project/FiiPython/)
[![License](https://img.shields.io/github/license/yourusername/FiiPython.svg)](https://github.com/Xing-yuyu/FiiPython/blob/main/LICENSE)

一个用于解析FII文件、计算无人机运动状态并生成可视化视频的仿真系统。

## ✨ 特性

- 🚁 **解析FII文件** - 读取XML格式的动作文件，提取起飞、移动、灯光等指令
- 📊 **连续运动计算** - 支持加减速，保留速度信息，运动平滑自然
- 🎮 **实时仿真显示** - 可调节帧率，支持多视角（俯视图、前视图、右视图）
- 🎥 **高清视频生成** - 支持带音频的视频输出，内存优化设计
- 💾 **内存优化** - 分批处理帧数据，避免内存溢出
- 🎨 **灯光效果** - 支持闪烁、呼吸、跑马灯等多种灯光效果

## 📦 安装

### 从源码安装

```bash
git clone https://github.com/Xing-yuyu/FiiPython.git
cd FiiPython
pip install -e .
```

## 🎯 使用
```python
import FiiPython as fp
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='无人机仿真显示')
    parser.add_argument('--show-fps', type=int, default=60, help='显示帧率')
    parser.add_argument('--video-fps', type=int, default=60, help='视频帧率')
    parser.add_argument('--simulate', action='store_true', default=True, help='是否显示模拟窗口')
    parser.add_argument('--save', action='store_true', default=True, help='是否保存视频')
    parser.add_argument('--save-as', type=str, default='video.mp4', help='保存文件名')
    parser.add_argument('--clarity', type=int, default=1, help='清晰度')
    parser.add_argument('--max-memory', type=int, default=1024, help='最大内存使用(MB)')

    args = parser.parse_args()

    print("读取FII文件...")
    size, takeoff_pos_list, final_dict_list = fp.readFii()
    print(f"无人机数量: {len(takeoff_pos_list)}")

    print("计算状态...")
    states_list = fp.caculateState(takeoff_pos_list, final_dict_list)

    print("生成视频/显示...")
    fp.show(
        states_list,
        size,
        show_fps=args.show_fps,
        simulate=args.simulate,
        save=args.save,
        save_as=args.save_as,
        video_fps=args.video_fps,
        clarity=args.clarity,
        max_memory_mb=args.max_memory
    )
```
