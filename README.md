# FiiPython - FII无人机仿真系统

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![PyPI version](https://img.shields.io/pypi/v/FiiPython.svg)
![License](https://img.shields.io/github/license/Xing-yuyu/FiiPython.svg)
![Downloads](https://img.shields.io/pypi/dm/FiiPython.svg)
![GitHub stars](https://img.shields.io/github/stars/Xing-yuyu/FiiPython?style=social)

**[English](#english) | [中文](#chinese)**

</div>

---
<a name="chinese"></a>
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

命令行使用
```bash
# 在当前目录查找.fii文件并显示仿真
fiipython-simulate --simulate True

# 保存视频（不显示窗口）
fiipython-simulate --save True --save-as output.mp4

# 高帧率显示
fiipython-simulate --show-fps 120 --simulate True

# 简单显示模式
fiipython-show

# 查看帮助
fiipython-simulate --help
```
Python代码中使用
```python
from FiiPython import readFii, caculateState, show

# 1. 读取FII文件
size, takeoff_pos_list, final_dict_list = readFii('./')

# 2. 计算运动状态
states_list = caculateState(takeoff_pos_list, final_dict_list)

# 3. 显示仿真
show(states_list, size, simulate=True, save=False)

# 4. 或者保存高清视频
show(
    states_list,
    size,
    simulate=False,
    save=True,
    save_as='output.mp4',
    video_fps=60,
    clarity=2  # 2倍清晰度
)
```
📁 文件结构要求
```text
你的项目目录/
├── 动作组/                    # 存放各无人机的XML动作文件
│   ├── 动作组1/
│   │   ├── 1.xml
│   │   ├── 2.xml
│   │   └── ...
│   ├── 动作组2/
│   │   └── ...
│   └── ... 
├── your_file.fii              # 主FII文件（必需）
└── background.mp3             # 背景音乐（可选，自动加载）
```
⚙️ 参数说明

参数  说明  默认值 示例

show_fps    显示帧率    60  --show-fps 30

video_fps   视频帧率    60  --video-fps 120

simulate    是否显示窗口  False   --simulate True

save    是否保存视频  True    --save False

save_as 保存文件名   video.mp4   --save-as result.mp4

clarity 清晰度倍数   1   --clarity 2

max_memory_mb   最大内存使用(MB)  1024    --max-memory 2048

fii-file    FII文件路径 ./  --fii-file ./test.fii

🎯 运动指令示例
在XML文件中可以使用的运动指令：

```xml
<!-- 起飞到高度100cm -->
<block type="Goertek_TakeOff2">
    <field name="height">100</field>
</block>

<!-- 绝对移动到坐标(200,150,80) -->
<block type="Goertek_MoveToCoord2">
    <field name="x">200</field>
    <field name="y">150</field>
    <field name="z">80</field>
</block>

<!-- 相对移动：x+50, y-30, z不变 -->
<block type="Goertek_Move">
    <field name="x">50</field>
    <field name="y">-30</field>
    <field name="z">0</field>
</block>

<!-- 降落 -->
<block type="Goertek_Land">
</block>
```
🎨 灯光效果示例
```xml
<!-- 全身呼吸灯 -->
<block type="Goertek_LEDBreathALL2">
    <field name="time1">1000</field>
    <field name="color">#FF0000</field>
    <field name="brightness">0.8</field>
    <field name="time2">1000</field>
</block>

<!-- 跑马灯 -->
<block type="Goertek_LEDHorseALL4">
    <field name="color1">#FF0000</field>
    <field name="color2">#00FF00</field>
    <field name="color3">#0000FF</field>
    <field name="color4">#FFFF00</field>
    <field name="clock">True</field>
    <field name="delay">200</field>
</block>
```
🏗️ 项目结构
```text
FiiPython/
├── FiiPython/                 # 主代码包
│   ├── __init__.py            # 包初始化
│   ├── ReadFii.py             # FII文件解析
│   ├── CaculateState.py       # 运动状态计算
│   ├── DrawDrone.py           # 可视化绘制
│   ├── VideoSaver.py          # 视频保存
│   └── utils.py               # 工具函数
├── scripts/                    # 命令行脚本
│   ├── run_simulation.py      # 主运行脚本
│   └── show.py                 # 简单显示脚本
├── tests/                       # 测试目录
├── examples/                    # 示例代码
├── README.md                    # 本文档
├── LICENSE                      # MIT许可证
├── pyproject.toml               # 项目配置
└── requirements.txt             # 依赖列表
```
📊 性能优化
对于长时间仿真或高清晰度视频，建议：

```python
# 限制内存使用
show(
    states_list,
    size,
    max_memory_mb=2048,  # 使用2GB内存
    video_fps=30,        # 降低帧率减少内存
    clarity=1            # 保持标准清晰度
)
```
🤝 贡献指南
欢迎贡献代码、报告问题或提出新特性！

Fork 本仓库

创建你的特性分支 (git checkout -b feature/AmazingFeature)

提交你的修改 (git commit -m 'Add some AmazingFeature')

推送到分支 (git push origin feature/AmazingFeature)

打开一个 Pull Request

📝 更新日志

v1.0.0 (2024-03-08)

🎉 首次发布

✨ 支持FII文件解析

✨ 支持连续运动计算（保留速度）

✨ 支持三视图显示

✨ 支持视频生成和音频合成

✨ 支持多种灯光效果

v1.0.2 (2024-03-13)

✨ 修复未知bug

v1.0.3 (2024-03-18)

✨ 修复跑马灯模拟

✨ 修复模拟自动增加五秒延迟

✨ 修复之前误操作删掉的灯光

✨ 修复高分辨率框消失问题

v1.1.0 (计划中)

🖼️ 添加3D视图

📊 支持GPU渲染

🎮 补充波浪运动，点头

📄 许可证
本项目采用 MIT 许可证 - 详见 LICENSE 文件

📬 联系方式
作者: Xing-yuyu

GitHub: @Xing-yuyu

项目地址: https://github.com/Xing-yuyu/FiiPython

问题反馈: Issues

🙏 致谢
感谢所有为这个项目提供帮助和建议的朋友们！