# VideoSaver.py (最终修复版)
import cv2
import numpy as np
import os
import tempfile
import subprocess
from typing import Iterator, List, Optional, Union, Callable, Tuple, Generator
import gc


class VideoSaver:
    """内存优化的视频保存工具 - 使用生成器逐帧处理"""

    def __init__(self, fps: int = 30):
        """
        初始化视频保存器

        Args:
            fps: 视频帧率 (帧/秒)
        """
        self.fps = fps

    def save_video_from_generator(self,
                                  frame_generator: Iterator[np.ndarray],
                                  output_path: str,
                                  total_frames: Optional[int] = None,
                                  audio_path: Optional[str] = None,
                                  progress_callback: Optional[Callable] = None,
                                  frame_color_mode: str = 'BGR') -> bool:
        """
        从生成器保存视频（内存优化）

        Args:
            frame_generator: 帧生成器，逐个产生帧
            output_path: 输出路径
            total_frames: 总帧数（用于进度显示）
            audio_path: 音频文件路径
            progress_callback: 进度回调函数
            frame_color_mode: 输入帧的颜色模式 ('RGB' 或 'BGR')
        """
        try:
            # 获取第一帧以确定尺寸
            first_frame = next(frame_generator)
            if len(first_frame.shape) == 2:
                height, width = first_frame.shape
            else:
                height, width = first_frame.shape[:2]

            print(f"视频尺寸: {width}x{height}, 颜色模式: {frame_color_mode}")

            # 确定输出路径
            temp_video = None
            if audio_path and os.path.exists(audio_path):
                temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                video_path = temp_video.name
                temp_video.close()
                print(f"创建临时视频文件: {video_path}")
            else:
                if audio_path and not os.path.exists(audio_path):
                    print(f"警告: 音频文件不存在: {audio_path}")
                video_path = output_path

            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(video_path, fourcc, self.fps, (width, height))

            if not out.isOpened():
                raise RuntimeError(f"无法创建视频文件: {video_path}")

            # 处理第一帧
            processed_frame = self._ensure_bgr_format(first_frame, frame_color_mode)
            out.write(processed_frame)
            frame_count = 1

            # 逐帧处理剩余帧
            for frame in frame_generator:
                processed_frame = self._ensure_bgr_format(frame, frame_color_mode)
                out.write(processed_frame)
                frame_count += 1

                # 进度回调
                if progress_callback:
                    progress_callback(frame_count)

                # 每30帧显示一次进度
                if total_frames and frame_count % 30 == 0:
                    print(f"已处理 {frame_count}/{total_frames} 帧", end='\r')
                elif frame_count % 30 == 0:
                    print(f"已处理 {frame_count} 帧", end='\r')

            out.release()
            print(f"\n视频保存完成: {video_path}，共 {frame_count} 帧")

            # 如果有音频，合成
            if audio_path and os.path.exists(audio_path) and temp_video:
                return self._merge_audio_simple(temp_video.name, audio_path, output_path)

            return True

        except StopIteration:
            print("错误: 帧生成器为空")
            return False
        except Exception as e:
            print(f"保存视频时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _ensure_bgr_format(self, frame: np.ndarray, input_mode: str) -> np.ndarray:
        """
        确保帧是BGR格式（OpenCV VideoWriter需要的格式）

        关键点：
        - 如果输入是RGB，需要转换为BGR
        - 如果输入是BGR，保持不变
        - 如果输入是灰度图，转换为BGR
        """
        # 处理灰度图
        if len(frame.shape) == 2:
            return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        # 处理彩色图
        if len(frame.shape) == 3:
            if input_mode.upper() == 'RGB':
                # RGB -> BGR
                return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            elif input_mode.upper() == 'RGBA':
                # RGBA -> BGR
                return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            elif input_mode.upper() == 'BGR':
                # 已经是BGR，保持不变
                return frame

        # 默认返回原图
        return frame

    def _merge_audio_simple(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """简单的ffmpeg音频合成"""
        try:
            # 检查ffmpeg
            try:
                subprocess.run(['ffmpeg', '-version'],
                               capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("警告: ffmpeg未找到，保存无音频版本")
                import shutil
                shutil.copy2(video_path, output_path)
                os.unlink(video_path)
                return True

            print(f"使用ffmpeg合成音频: {audio_path}")

            # 最简单的ffmpeg命令
            cmd = [
                'ffmpeg',
                '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c', 'copy',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True)

            if result.returncode != 0:
                # 如果直接复制失败，尝试map方式
                cmd2 = [
                    'ffmpeg',
                    '-y',
                    '-i', video_path,
                    '-i', audio_path,
                    '-map', '0:v',
                    '-map', '1:a',
                    '-c:v', 'copy',
                    '-c:a', 'copy',
                    output_path
                ]

                result2 = subprocess.run(cmd2, capture_output=True)

                if result2.returncode != 0:
                    print("音频合成失败，保存无音频版本")
                    import shutil
                    shutil.copy2(video_path, output_path)
                else:
                    print("音频合成成功（使用map方式）")

            # 删除临时视频文件
            if os.path.exists(video_path):
                os.unlink(video_path)

            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                print(f"✅ 视频合成成功: {output_path}")
                print(f"   文件大小: {file_size:.2f} MB")
                return True
            else:
                print(f"❌ 输出文件未生成")
                return False

        except Exception as e:
            print(f"音频合成时出错: {e}")
            return False