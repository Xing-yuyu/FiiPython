#!/usr/bin/env python3
"""命令行运行脚本"""

import argparse
import sys
import os

# 添加父目录到路径，以便直接运行脚本
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FiiPython import readFii, caculateState, show


def main():
    parser = argparse.ArgumentParser(description='FiiPython - FII无人机仿真系统')
    parser.add_argument('--show-fps', type=int, default=60, help='显示帧率')
    parser.add_argument('--video-fps', type=int, default=60, help='视频帧率')
    parser.add_argument('--simulate', action='store_true', default=False, help='是否显示模拟窗口')
    parser.add_argument('--save', action='store_true', default=True, help='是否保存视频')
    parser.add_argument('--save-as', type=str, default='video.mp4', help='保存文件名')
    parser.add_argument('--clarity', type=int, default=1, help='清晰度倍数')
    parser.add_argument('--max-memory', type=int, default=1024, help='最大内存使用(MB)')
    parser.add_argument('--fii-file', type=str, default='./', help='FII文件路径或目录')

    args = parser.parse_args()

    print("=" * 60)
    print("FiiPython - FII无人机仿真系统")
    print("=" * 60)

    try:
        print("读取FII文件...")
        size, takeoff_pos_list, final_dict_list = readFii(args.fii_file)

        print(f"无人机数量: {len(takeoff_pos_list)}")
        print(f"场地尺寸: {size}cm")

        print("计算运动状态...")
        states_list = caculateState(takeoff_pos_list, final_dict_list)

        print("生成视频/显示...")
        show(
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

        print("\n✅ 仿真完成！")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())