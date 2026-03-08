# show.py (修复版)
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