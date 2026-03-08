# FiiPython - FII无人机仿真系统

[![PyPI version](https://img.shields.io/pypi/v/FiiPython.svg)](https://pypi.org/project/FiiPython/)
[![Python versions](https://img.shields.io/pypi/pyversions/FiiPython.svg)](https://pypi.org/project/FiiPython/)
[![License](https://img.shields.io/github/license/yourusername/FiiPython.svg)](https://github.com/yourusername/FiiPython/blob/main/LICENSE)

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