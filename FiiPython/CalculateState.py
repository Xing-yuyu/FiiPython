# calculateState.py (添加相对移动功能)
import json
import math
from typing import Dict, List, Tuple, Optional, Any
from copy import deepcopy
import os


class LightEffect:
    """灯光效果基类"""

    def __init__(self, start_time: int):
        self.start_time = start_time

    def get_color(self, current_time: int) -> Tuple[int, int, int]:
        return (0, 0, 0)


class BlinkEffect(LightEffect):
    """闪烁效果：亮dur毫秒，灭delay毫秒，循环"""

    def __init__(self, start_time: int, color: Tuple[int, int, int],
                 brightness: float, dur: int, delay: int):
        super().__init__(start_time)
        self.color = color
        self.brightness = brightness
        self.dur = dur
        self.delay = delay
        self.cycle = dur + delay

    def get_color(self, current_time: int) -> Tuple[int, int, int]:
        time_in_cycle = (current_time - self.start_time) % self.cycle
        if time_in_cycle < self.dur:
            # 亮灯
            return tuple(int(min(255, c * self.brightness)) for c in self.color)
        else:
            # 灭灯
            return (0, 0, 0)


class BreathEffect(LightEffect):
    """呼吸效果：time1内从0变到颜色，time2内从颜色变到0，循环"""

    def __init__(self, start_time: int, color: Tuple[int, int, int],
                 time1: int, time2: int, brightness: float):
        super().__init__(start_time)
        self.color = color
        self.time1 = time1
        self.time2 = time2
        self.brightness = brightness
        self.cycle = time1 + time2

    def get_color(self, current_time: int) -> Tuple[int, int, int]:
        time_in_cycle = (current_time - self.start_time) % self.cycle

        if time_in_cycle < self.time1:
            # 亮度上升
            ratio = time_in_cycle / self.time1
        else:
            # 亮度下降
            ratio = 1 - (time_in_cycle - self.time1) / self.time2

        return tuple(int(min(255, c * self.brightness * ratio)) for c in self.color)


class MotorHorseEffect(LightEffect):
    """
    跑马灯效果：四个马达依次变色

    参数:
        start_time: 开始时间(ms)
        colors: 四个马达的颜色列表 [[r,g,b], [r,g,b], [r,g,b], [r,g,b]]
        clock: True=顺时针, False=逆时针
        delay: 跑完一圈的总时间(ms)，每个马达显示时间为 delay/4
    """

    def __init__(self, start_time: int, colors: List[Tuple[int, int, int]],
                 clock: bool, delay: int):
        super().__init__(start_time)
        self.colors = colors
        self.clock = clock  # True:顺时针, False:逆时针
        self.delay = delay
        self.num_colors = len(colors)

        # 每个马达的显示时间
        self.step_duration = delay / 4  # 每个马达显示的时间

        print(f"  跑马灯初始化: colors={colors}, clock={clock}, delay={delay}ms, step={self.step_duration}ms")

    def get_motor_colors(self, current_time: int) -> Dict[int, Tuple[int, int, int]]:
        """
        获取当前时间各个马达的颜色

        跑马灯逻辑：
        - 总周期 = delay ms
        - 每个马达显示 delay/4 ms
        - 顺时针顺序: 1->2->3->4->1...
        - 逆时针顺序: 4->3->2->1->4...

        Args:
            current_time: 当前时间(ms)

        Returns:
            Dict[int, Tuple[int,int,int]]: 马达编号->颜色 的字典
        """
        # 计算当前时间相对于开始时间的偏移
        time_offset = current_time - self.start_time
        if time_offset < 0:
            time_offset = 0

        # 计算当前在哪个步骤 (0,1,2,3 循环)
        # 每个步骤持续 step_duration ms
        step = int((time_offset / self.step_duration) % 4)

        result = {}

        if self.clock:  # 顺时针: 1->2->3->4
            # 马达1: 当前step的颜色
            result[1] = self.colors[step % 4]
            # 马达2: 下一个step的颜色
            result[2] = self.colors[(step + 1) % 4]
            # 马达3: 下两个step的颜色
            result[3] = self.colors[(step + 2) % 4]
            # 马达4: 下三个step的颜色
            result[4] = self.colors[(step + 3) % 4]

        else:  # 逆时针: 4->3->2->1
            # 马达4: 当前step的颜色
            result[4] = self.colors[step % 4]
            # 马达3: 下一个step的颜色
            result[3] = self.colors[(step + 1) % 4]
            # 马达2: 下两个step的颜色
            result[2] = self.colors[(step + 2) % 4]
            # 马达1: 下三个step的颜色
            result[1] = self.colors[(step + 3) % 4]

        return result

    def get_color(self, current_time: int) -> Tuple[int, int, int]:
        """
        基类方法，这里用不到，因为MotorHorse是给马达用的
        """
        return (0, 0, 0)

class MovementState:
    """运动状态 - 单位：厘米(cm)"""

    def __init__(self, takeoff_pos: List[float]):
        """
        :param takeoff_pos: 起飞点坐标 [x, y] (cm)
        """
        self.takeoff_pos = takeoff_pos  # 起飞点
        self.pos = [takeoff_pos[0], takeoff_pos[1], 0.0]  # 当前位置

        # 默认速度 [速度(cm/s), 加速度(cm/s²)]
        self.xy_speed = [100.0, 100.0]  # [速度, 加速度]
        self.z_speed = [100.0, 100.0]   # [速度, 加速度]

        self.is_flying = False  # 是否在飞行中

        # ========== 普通运动状态 ==========
        self.normal_move = {
            'active': False,
            'start_time': 0,
            'start_pos': [takeoff_pos[0], takeoff_pos[1], 0.0],
            'target_pos': [takeoff_pos[0], takeoff_pos[1], 0.0],
            'target_vx': 0.0,
            'target_vy': 0.0,
            'target_vz': 0.0,
            'duration': 0,
            'end_time': 0
        }

        # ========== 简谐运动状态 ==========
        self.harmonic = {
            'active': False,
            'start_time': 0,
            'start_pos': [takeoff_pos[0], takeoff_pos[1], 0.0],
            'axis': 'x',
            'direction': 1,  # 1 或 -1
            'amplitude': 0.0,
            'duration': 5000,  # 固定5秒
            'end_time': 0,
            'phase1_end': 0,
            'phase2_end': 0,
            'phase3_end': 0
        }

        # 当前运动的速度 (cm/s)
        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_vz = 0.0

        self.last_command_time = 0  # 最后指令时间

    def _get_current_velocity(self) -> Tuple[float, float, float]:
        """获取当前时刻的实际速度"""
        return (self.current_vx, self.current_vy, self.current_vz)

    # ========== 普通运动方法 ==========

    def takeoff(self, height: float, current_time: int):
        """起飞到指定高度"""
        self.is_flying = True
        self._stop_harmonic()  # 停止任何进行中的简谐运动

        # 设置普通运动
        self.normal_move['active'] = True
        self.normal_move['start_time'] = current_time
        self.normal_move['start_pos'] = self.pos.copy()
        self.normal_move['target_pos'] = [self.takeoff_pos[0], self.takeoff_pos[1], height]

        # 计算运动参数
        distance = height - self.pos[2]
        direction = 1 if distance > 0 else -1
        self.normal_move['target_vz'] = self.z_speed[0] * direction

        # 估算时间
        abs_distance = abs(distance)
        v_max = self.z_speed[0]
        a = self.z_speed[1]

        if a > 0:
            accel_dist = v_max * v_max / (2 * a)
            if abs_distance <= 2 * accel_dist:
                v_peak = math.sqrt(a * abs_distance)
                self.normal_move['duration'] = 2 * v_peak / a
            else:
                accel_time = v_max / a
                const_dist = abs_distance - 2 * accel_dist
                const_time = const_dist / v_max
                self.normal_move['duration'] = 2 * accel_time + const_time
        else:
            self.normal_move['duration'] = abs_distance / v_max if v_max > 0 else 0

        self.normal_move['end_time'] = current_time + int(self.normal_move['duration'] * 1000)

        print(f"  起飞: 从{self.normal_move['start_pos']}到{self.normal_move['target_pos']}, 需要{self.normal_move['duration']:.2f}s")

    def land(self, current_time: int):
        """降落 - 有运动过程"""
        if self.pos[2] <= 0:
            print(f"  已经在 ground")
            return

        self._stop_harmonic()  # 停止任何进行中的简谐运动

        self.normal_move['active'] = True
        self.normal_move['start_time'] = current_time
        self.normal_move['start_pos'] = self.pos.copy()
        self.normal_move['target_pos'] = [self.pos[0], self.pos[1], 0.0]

        # 设置运动参数（减速下降）
        distance = -self.pos[2]
        self.normal_move['target_vz'] = -self.z_speed[0]

        # 估算时间
        abs_distance = self.pos[2]
        v_max = self.z_speed[0]
        a = self.z_speed[1]

        if a > 0:
            decel_dist = v_max * v_max / (2 * a)
            if abs_distance <= decel_dist:
                self.normal_move['duration'] = v_max / a
            else:
                const_dist = abs_distance - decel_dist
                const_time = const_dist / v_max
                decel_time = v_max / a
                self.normal_move['duration'] = const_time + decel_time
        else:
            self.normal_move['duration'] = abs_distance / v_max if v_max > 0 else 0

        self.normal_move['end_time'] = current_time + int(self.normal_move['duration'] * 1000)

        print(f"  降落: 从高度{self.pos[2]:.1f}cm到地面, 需要{self.normal_move['duration']:.2f}s")

    def move_to(self, target: List[float], current_time: int):
        """移动到目标点（绝对移动）"""
        self._stop_harmonic()  # 停止任何进行中的简谐运动

        self.normal_move['active'] = True
        self.normal_move['start_time'] = current_time
        self.normal_move['start_pos'] = self.pos.copy()
        self.normal_move['target_pos'] = target

        # 计算各轴位移
        dx = target[0] - self.pos[0]
        dy = target[1] - self.pos[1]
        dz = target[2] - self.pos[2]

        print(f"  绝对移动: 从{self.normal_move['start_pos']}到{self.normal_move['target_pos']}")
        print(f"        当前速度: vx={self.current_vx:.1f}, vy={self.current_vy:.1f}, vz={self.current_vz:.1f}")

        # 设置目标速度
        if abs(dx) > 0.001:
            self.normal_move['target_vx'] = self.xy_speed[0] if dx > 0 else -self.xy_speed[0]
        else:
            self.normal_move['target_vx'] = 0

        if abs(dy) > 0.001:
            self.normal_move['target_vy'] = self.xy_speed[0] if dy > 0 else -self.xy_speed[0]
        else:
            self.normal_move['target_vy'] = 0

        if abs(dz) > 0.001:
            self.normal_move['target_vz'] = self.z_speed[0] if dz > 0 else -self.z_speed[0]
        else:
            self.normal_move['target_vz'] = 0

        # 估算时间
        time_x = abs(dx) / self.xy_speed[0] if abs(dx) > 0.001 else 0
        time_y = abs(dy) / self.xy_speed[0] if abs(dy) > 0.001 else 0
        time_z = abs(dz) / self.z_speed[0] if abs(dz) > 0.001 else 0

        self.normal_move['duration'] = max(time_x, time_y, time_z)
        if self.normal_move['duration'] <= 0:
            self.normal_move['duration'] = 0.001

        self.normal_move['end_time'] = current_time + int(self.normal_move['duration'] * 1000)

        print(f"        目标速度: vx={self.normal_move['target_vx']:.1f}, vy={self.normal_move['target_vy']:.1f}, vz={self.normal_move['target_vz']:.1f}")
        print(f"        总时间: {self.normal_move['duration']:.2f}s")

    def move(self, offset: List[float], current_time: int):
        """相对移动"""
        target = [
            self.pos[0] + offset[0],
            self.pos[1] + offset[1],
            self.pos[2] + offset[2]
        ]
        print(f"  相对移动: 偏移{offset} -> 目标位置{target}")
        self.move_to(target, current_time)

    # ========== 简谐运动方法 ==========

    def start_simple_harmonic(self, axis: str, amplitude: float, current_time: int):
        """开始简谐运动"""
        # 停止任何进行中的普通运动
        self.normal_move['active'] = False

        # 解析方向和轴
        axis_input = axis.lower()
        if axis_input.startswith('-'):
            direction = -1
            axis_name = axis_input[1:]
        else:
            direction = 1
            axis_name = axis_input

        # 设置简谐运动状态
        self.harmonic['active'] = True
        self.harmonic['start_time'] = current_time
        self.harmonic['start_pos'] = self.pos.copy()
        self.harmonic['axis'] = axis_name
        self.harmonic['direction'] = direction
        self.harmonic['amplitude'] = amplitude
        self.harmonic['end_time'] = current_time + 5000

        # 计算三个阶段的时间点
        self.harmonic['phase1_end'] = current_time + 1250  # 0-1.25s
        self.harmonic['phase2_end'] = current_time + 3750  # 1.25-3.75s
        self.harmonic['phase3_end'] = current_time + 5000  # 3.75-5.0s

        direction_str = "正向" if direction > 0 else "负向"
        print(f"  简谐运动开始: {axis_input}轴, 方向={direction_str}, 振幅={amplitude}cm")
        print(f"    起始位置: {self.pos}")

    def _stop_harmonic(self):
        """停止简谐运动，清理状态"""
        if self.harmonic['active']:
            self.harmonic['active'] = False
            print(f"    简谐运动被中断，当前位置: {self.pos}")

    # ========== 位置计算方法 ==========

    def calculate_position(self, current_time: int) -> List[float]:
        """计算当前位置"""
        # 优先处理简谐运动
        if self.harmonic['active']:
            return self._calculate_harmonic_position(current_time)

        # 处理普通运动
        if self.normal_move['active']:
            return self._calculate_normal_position(current_time)

        # 没有运动，返回当前位置
        return self.pos.copy()

    def _calculate_normal_position(self, current_time: int) -> List[float]:
        """计算普通运动位置"""
        move = self.normal_move
        dt = (current_time - move['start_time']) / 1000.0

        # 如果还没开始
        if dt <= 0:
            return self.pos.copy()

        # 如果已经结束
        if dt >= move['duration']:
            self.pos = move['target_pos'].copy()
            self.current_vx = 0
            self.current_vy = 0
            self.current_vz = 0
            self.normal_move['active'] = False
            if move['target_pos'][2] == 0:
                self.is_flying = False
            return self.pos.copy()

        # 计算进度
        progress = dt / move['duration']

        # 线性插值
        x = move['start_pos'][0] + (move['target_pos'][0] - move['start_pos'][0]) * progress
        y = move['start_pos'][1] + (move['target_pos'][1] - move['start_pos'][1]) * progress
        z = move['start_pos'][2] + (move['target_pos'][2] - move['start_pos'][2]) * progress

        # 更新速度
        self.current_vx = move['target_vx'] * (1 - progress) if abs(move['target_vx']) > 0 else 0
        self.current_vy = move['target_vy'] * (1 - progress) if abs(move['target_vy']) > 0 else 0
        self.current_vz = move['target_vz'] * (1 - progress) if abs(move['target_vz']) > 0 else 0

        self.pos = [x, y, z]
        return [x, y, z]

    def _calculate_harmonic_position(self, current_time: int) -> List[float]:
        """计算简谐运动位置"""
        h = self.harmonic

        # 如果还没开始
        if current_time < h['start_time']:
            return self.pos.copy()

        # 如果已经结束
        if current_time >= h['end_time']:
            # 回到原点
            self.pos = h['start_pos'].copy()
            self.current_vx = 0
            self.current_vy = 0
            self.current_vz = 0
            self.harmonic['active'] = False
            print(f"    简谐运动结束，回到原点: {self.pos}")
            return self.pos.copy()

        # 计算位移
        displacement = self._calculate_harmonic_displacement(current_time)

        # 计算新位置
        new_pos = h['start_pos'].copy()
        axis = h['axis']

        if axis == 'x':
            new_pos[0] = h['start_pos'][0] + displacement
            # 计算速度
            vel = self._calculate_harmonic_velocity(current_time)
            self.current_vx = vel
            self.current_vy = 0
            self.current_vz = 0
        elif axis == 'y':
            new_pos[1] = h['start_pos'][1] + displacement
            vel = self._calculate_harmonic_velocity(current_time)
            self.current_vx = 0
            self.current_vy = vel
            self.current_vz = 0
        elif axis == 'z':
            new_pos[2] = h['start_pos'][2] + displacement
            vel = self._calculate_harmonic_velocity(current_time)
            self.current_vx = 0
            self.current_vy = 0
            self.current_vz = vel

        self.pos = new_pos
        return new_pos

    def _calculate_harmonic_displacement(self, current_time: int) -> float:
        """计算简谐运动位移"""
        h = self.harmonic
        t = current_time - h['start_time']
        A = h['amplitude']
        direction = h['direction']

        # 阶段1: 0-1250ms, 正向移动 A
        if current_time <= h['phase1_end']:
            progress = t / 1250.0
            base = A * progress

        # 阶段2: 1250-3750ms, 反向移动 2A
        elif current_time <= h['phase2_end']:
            t2 = t - 1250
            progress = t2 / 2500.0
            base = A - 2 * A * progress

        # 阶段3: 3750-5000ms, 正向移动 A
        else:
            t3 = t - 3750
            progress = t3 / 1250.0
            base = -A + A * progress

        return base * direction

    def _calculate_harmonic_velocity(self, current_time: int) -> float:
        """计算简谐运动速度 (cm/s)"""
        h = self.harmonic
        A = h['amplitude']
        direction = h['direction']

        # 阶段1速度: A / 1.25s = A * 0.8 cm/s
        if current_time <= h['phase1_end']:
            base_vel = A * 0.8  # A / 1.25

        # 阶段2速度: -2A / 2.5s = -A * 0.8 cm/s
        elif current_time <= h['phase2_end']:
            base_vel = -A * 0.8  # -2A / 2.5

        # 阶段3速度: A / 1.25s = A * 0.8 cm/s
        else:
            base_vel = A * 0.8

        return base_vel * direction

    def update_speed(self, xy_speed: List[float] = None, z_speed: List[float] = None):
        """更新速度设置"""
        if xy_speed:
            self.xy_speed = xy_speed
        if z_speed:
            self.z_speed = z_speed

class SimpleHarmonicEffect:
    """
    简谐运动效果：往返运动

    参数:
        start_time: 开始时间(ms)
        axis: 运动轴 'x', 'y', 'z' (带方向或不带方向)
        amplitude: 振幅(cm)
        duration: 总持续时间(ms) = 5000ms (固定)

    方向说明:
        'x', 'y', 'z' - 正向移动
        '-x', '-y', '-z' - 负向移动

    运动规律（以正向为例）：
        0-1.25s:  沿axis方向移动 amplitude
        1.25-3.75s: 向相反方向移动 2*amplitude
        3.75-5.0s:  沿axis方向移动 amplitude (回到原点)
    """

    def __init__(self, start_time: int, axis: str, amplitude: float, duration: int = 5000):
        self.start_time = start_time
        self.axis_input = axis.lower()
        self.amplitude = amplitude
        self.duration = duration  # 固定5000ms

        # 解析方向和实际轴
        if self.axis_input.startswith('-'):
            self.direction = -1  # 负方向
            self.axis = self.axis_input[1:]  # 去掉负号
        else:
            # 处理可能带 '+' 的情况
            if self.axis_input.startswith('+'):
                self.axis = self.axis_input[1:]
            else:
                self.axis = self.axis_input
            self.direction = 1  # 正方向

        # 三个阶段的时间点
        self.phase1_end = start_time + duration // 4  # 0-1.25s: 正向移动 amplitude
        self.phase2_end = start_time + duration * 3 // 4  # 1.25-3.75s: 反向移动 2*amplitude
        self.phase3_end = start_time + duration  # 3.75-5.0s: 正向移动 amplitude

        direction_str = "正向" if self.direction > 0 else "负向"
        print(f"  简谐运动: axis={self.axis}, 方向={direction_str}, amplitude={amplitude}cm, duration={duration}ms")
        print(f"    阶段1: {start_time}->{self.phase1_end}ms, {direction_str}{amplitude}cm")
        print(f"    阶段2: {self.phase1_end}->{self.phase2_end}ms, 反向{2 * amplitude}cm")
        print(f"    阶段3: {self.phase2_end}->{self.phase3_end}ms, {direction_str}{amplitude}cm")

    def is_active(self, current_time: int) -> bool:
        """检查简谐运动是否仍在进行中"""
        time_in_cycle = current_time - self.start_time
        return 0 <= time_in_cycle < self.duration

    def get_displacement(self, current_time: int) -> float:
        """
        获取当前时间相对于起始点的位移

        Args:
            current_time: 当前时间(ms)

        Returns:
            位移量(cm)，正数表示沿axis正方向
        """
        time_in_cycle = current_time - self.start_time

        # 还没开始
        if time_in_cycle <= 0:
            return 0.0

        # 超过总时间，回到原点
        if time_in_cycle >= self.duration:
            return 0.0

        # 计算基础位移（假设方向为正）
        base_displacement = 0.0

        # 阶段1: 正向移动 amplitude (0 -> +amplitude)
        if current_time <= self.phase1_end:
            progress = (current_time - self.start_time) / (self.duration / 4)
            base_displacement = self.amplitude * progress

        # 阶段2: 反向移动 2*amplitude (+amplitude -> -amplitude)
        elif current_time <= self.phase2_end:
            # 计算在阶段2中的进度
            phase2_progress = (current_time - self.phase1_end) / (self.duration / 2)
            # 从 +amplitude 线性降到 -amplitude
            base_displacement = self.amplitude - 2 * self.amplitude * phase2_progress

        # 阶段3: 正向移动 amplitude (-amplitude -> 0)
        else:
            # 计算在阶段3中的进度
            phase3_progress = (current_time - self.phase2_end) / (self.duration / 4)
            # 从 -amplitude 线性升到 0
            base_displacement = -self.amplitude + self.amplitude * phase3_progress

        # 根据方向调整位移
        return base_displacement * self.direction

    def get_velocity(self, current_time: int) -> float:
        """
        获取当前时间的速度

        Returns:
            速度(cm/ms)，需要转换为cm/s时乘以1000
        """
        time_in_cycle = current_time - self.start_time

        if time_in_cycle <= 0 or time_in_cycle >= self.duration:
            return 0.0

        # 各阶段的基础速度（每毫秒的位移）
        base_velocity = 0.0

        if current_time <= self.phase1_end:
            # 阶段1速度 = amplitude / (duration/4)
            base_velocity = self.amplitude / (self.duration / 4)
        elif current_time <= self.phase2_end:
            # 阶段2速度 = -2*amplitude / (duration/2)
            base_velocity = -2 * self.amplitude / (self.duration / 2)
        else:
            # 阶段3速度 = amplitude / (duration/4)
            base_velocity = self.amplitude / (self.duration / 4)

        # 根据方向调整速度
        return base_velocity * self.direction

class LightState:
    """灯光状态管理器"""

    def __init__(self):
        # 各部分的常亮颜色
        self.body_color = (0, 0, 0)
        self.motor_colors = {i: (0, 0, 0) for i in range(1, 5)}

        # 各部分的灯光效果
        self.body_effect: Optional[LightEffect] = None
        self.motor_effects: Dict[int, Optional[LightEffect]] = {i: None for i in range(1, 5)}
        self.motor_horse_effect: Optional[MotorHorseEffect] = None

        # 记录最后一次设置的常亮颜色
        self.last_body_color = (0, 0, 0)
        self.last_motor_colors = {i: (0, 0, 0) for i in range(1, 5)}

    def handle_command(self, cmd_key: str, cmd_value: Any, current_time: int):
        """处理灯光指令"""

        # 全局灯光指令
        if cmd_key == 'AllOn':
            color = cmd_value
            self.body_color = color
            self.last_body_color = color
            for i in range(1, 5):
                self.motor_colors[i] = color
                self.last_motor_colors[i] = color
            self.body_effect = None
            self.motor_horse_effect = None
            for i in range(1, 5):
                self.motor_effects[i] = None
            print(f"  灯光: 全部亮 {color}")

        elif cmd_key == 'AllOff':
            self.body_color = (0, 0, 0)
            self.last_body_color = (0, 0, 0)
            for i in range(1, 5):
                self.motor_colors[i] = (0, 0, 0)
                self.last_motor_colors[i] = (0, 0, 0)
            self.body_effect = None
            self.motor_horse_effect = None
            for i in range(1, 5):
                self.motor_effects[i] = None
            print(f"  灯光: 全部灭")

        elif cmd_key == 'AllBlink':
            effect = BlinkEffect(
                current_time,
                cmd_value['color'],
                cmd_value.get('brightness', 1.0),
                cmd_value['dur'],
                cmd_value['delay']
            )
            self.body_effect = effect
            self.motor_horse_effect = None
            for i in range(1, 5):
                self.motor_effects[i] = effect
            print(f"  灯光: 全部闪烁 {cmd_value['color']}, dur={cmd_value['dur']}ms, delay={cmd_value['delay']}ms")

        elif cmd_key == 'AllBreath':
            effect = BreathEffect(
                current_time,
                cmd_value['color'],
                cmd_value['time1'],
                cmd_value['time2'],
                cmd_value.get('brightness', 1.0)
            )
            self.body_effect = effect
            self.motor_horse_effect = None
            for i in range(1, 5):
                self.motor_effects[i] = effect
            print(f"  灯光: 全部呼吸 {cmd_value['color']}, time1={cmd_value['time1']}ms, time2={cmd_value['time2']}ms")

        # 机身灯光指令
        elif cmd_key == 'BodyOn':
            self.body_color = cmd_value
            self.last_body_color = cmd_value
            self.body_effect = None
            print(f"  灯光: 机身亮 {cmd_value}")

        elif cmd_key == 'BodyOff':
            self.body_color = (0, 0, 0)
            self.last_body_color = (0, 0, 0)
            self.body_effect = None
            print(f"  灯光: 机身灭")

        elif cmd_key == 'BodyBlink':
            effect = BlinkEffect(
                current_time,
                cmd_value['color'],
                cmd_value.get('brightness', 1.0),
                cmd_value['dur'],
                cmd_value['delay']
            )
            self.body_effect = effect
            print(f"  灯光: 机身闪烁 {cmd_value['color']}")

        elif cmd_key == 'BodyBreath':
            effect = BreathEffect(
                current_time,
                cmd_value['color'],
                cmd_value['time1'],
                cmd_value['time2'],
                cmd_value.get('brightness', 1.0)
            )
            self.body_effect = effect
            print(f"  灯光: 机身呼吸 {cmd_value['color']}")

        # 马达灯光指令
        elif cmd_key == 'MotorOn':
            motor = cmd_value['motor']
            color = cmd_value['color']
            if motor == 0:
                for i in range(1, 5):
                    self.motor_colors[i] = color
                    self.last_motor_colors[i] = color
                    self.motor_effects[i] = None
            else:
                self.motor_colors[motor] = color
                self.last_motor_colors[motor] = color
                self.motor_effects[motor] = None
            self.motor_horse_effect = None
            motor_str = "全部马达" if motor == 0 else f"马达{motor}"
            print(f"  灯光: {motor_str}亮 {color}")

        elif cmd_key == 'MotorOff':
            motor = cmd_value
            if motor == 0:
                for i in range(1, 5):
                    self.motor_colors[i] = (0, 0, 0)
                    self.last_motor_colors[i] = (0, 0, 0)
                    self.motor_effects[i] = None
            else:
                self.motor_colors[motor] = (0, 0, 0)
                self.last_motor_colors[motor] = (0, 0, 0)
                self.motor_effects[motor] = None
            self.motor_horse_effect = None
            motor_str = "全部马达" if motor == 0 else f"马达{motor}"
            print(f"  灯光: {motor_str}灭")

        elif cmd_key == 'MotorBlink':
            motor = cmd_value['motor']
            effect = BlinkEffect(
                current_time,
                cmd_value['color'],
                cmd_value.get('brightness', 1.0),
                cmd_value['dur'],
                cmd_value['delay']
            )
            if motor == 0:
                for i in range(1, 5):
                    self.motor_effects[i] = effect
                self.motor_horse_effect = None
            else:
                self.motor_effects[motor] = effect
            motor_str = "全部马达" if motor == 0 else f"马达{motor}"
            print(f"  灯光: {motor_str}闪烁 {cmd_value['color']}")

        elif cmd_key == 'MotorBreath':
            motor = cmd_value['motor']
            effect = BreathEffect(
                current_time,
                cmd_value['color'],
                cmd_value['time1'],
                cmd_value['time2'],
                cmd_value.get('brightness', 1.0)
            )
            if motor == 0:
                for i in range(1, 5):
                    self.motor_effects[i] = effect
                self.motor_horse_effect = None
            else:
                self.motor_effects[motor] = effect
            motor_str = "全部马达" if motor == 0 else f"马达{motor}"
            print(f"  灯光: {motor_str}呼吸 {cmd_value['color']}")


        elif cmd_key == 'MotorHorse':

            """

            跑马灯效果

            cmd_value 格式: {

                'colors': [[r,g,b], [r,g,b], [r,g,b], [r,g,b]],

                'clock': True/False,

                'delay': 800  # 一圈总时间(ms)

            }

            """

            colors = cmd_value['colors']

            clock = cmd_value['clock']

            delay = cmd_value['delay']

            # 创建跑马灯效果

            effect = MotorHorseEffect(

                current_time,

                colors,

                clock,

                delay

            )

            # 设置跑马灯效果，清除其他马达效果

            self.motor_horse_effect = effect

            for i in range(1, 5):
                self.motor_effects[i] = None

            direction = "顺时针" if clock else "逆时针"

            print(f"  灯光: 跑马灯 {direction}, 颜色序列={colors}, 一圈时间={delay}ms")

    def get_colors(self, current_time: int) -> Dict[str, Tuple[int, int, int]]:
        """获取当前所有灯光颜色"""
        result = {
            'body': (0, 0, 0),
            'motor1': (0, 0, 0),
            'motor2': (0, 0, 0),
            'motor3': (0, 0, 0),
            'motor4': (0, 0, 0)
        }

        # 处理机身
        if self.body_effect:
            result['body'] = self.body_effect.get_color(current_time)
        else:
            result['body'] = self.body_color

        # 处理跑马灯效果 - 优先于单独的马达效果
        if self.motor_horse_effect is not None:
            # 获取跑马灯各个马达的颜色
            motor_colors = self.motor_horse_effect.get_motor_colors(current_time)
            for motor, color in motor_colors.items():
                result[f'motor{motor}'] = color
        else:
            # 处理单独的马达效果
            for motor in range(1, 5):
                if self.motor_effects[motor]:
                    result[f'motor{motor}'] = self.motor_effects[motor].get_color(current_time)
                else:
                    result[f'motor{motor}'] = self.motor_colors[motor]

        return result


class DroneStateInterpolator:
    def __init__(self, input_keyframes: Dict[int, Dict[str, Any]], takeoff_pos: List[float] = [0, 0]):
        """
        初始化插值器
        :param input_keyframes: 关键帧数据，键为时间戳(毫秒)，值为指令字典
        :param takeoff_pos: 起飞点坐标 [x, y] (cm)
        """
        if not isinstance(input_keyframes, dict):
            raise ValueError(f"input_keyframes必须是字典类型，当前是: {type(input_keyframes)}")

        # 检查是否为空字典
        if not input_keyframes:
            print(f"警告: 无人机 {takeoff_pos} 的关键帧字典为空！")
            # 创建一个默认的关键帧
            input_keyframes = {0: {}}

        self.keyframes = dict(input_keyframes)
        self.sorted_keyframes = sorted(self.keyframes.items())

        if not self.sorted_keyframes:
            print(f"错误: sorted_keyframes 为空！")
            self.start_time = 0
            self.end_time = 0
        else:
            self.start_time = 0
            self.end_time = self.sorted_keyframes[-1][0]

        # 运动状态 - 传入起飞点
        self.movement = MovementState(takeoff_pos)

        # 灯光状态
        self.light = LightState()

        print(f"初始化完成")
        print(f"起飞点: {takeoff_pos} cm")
        print(f"时间范围: {self.start_time} - {self.end_time}ms")
        print(f"关键帧数量: {len(self.sorted_keyframes)}")

    def parse_command(self, cmd_key: str, cmd_value: Any, current_time: int):
        """解析单个指令"""

        # 运动控制指令
        if cmd_key == 'TakeOff':
            self.movement.takeoff(cmd_value, current_time)

        elif cmd_key == 'Land':
            self.movement.land(current_time)

        elif cmd_key == 'MoveTo':
            self.movement.move_to(cmd_value, current_time)

        elif cmd_key == 'Move':  # 新增相对移动指令
            self.movement.move(cmd_value, current_time)

        elif cmd_key == 'SimpleHarmonicMotion':  # 简谐运动指令
            # cmd_value 格式: {'axis': 'x', 'amplitude': 50}
            axis = cmd_value['axis']
            amplitude = float(cmd_value['amplitude'])
            self.movement.start_simple_harmonic(axis, amplitude, current_time)

        elif cmd_key == 'XYSpeed':
            self.movement.update_speed(xy_speed=cmd_value)

        elif cmd_key == 'ZSpeed':
            self.movement.update_speed(z_speed=cmd_value)

        # 灯光指令
        elif cmd_key in ['AllOn', 'AllOff', 'AllBlink', 'AllBreath',
                         'BodyOn', 'BodyOff', 'BodyBlink', 'BodyBreath',
                         'MotorOn', 'MotorOff', 'MotorBlink', 'MotorBreath', 'MotorHorse']:
            self.light.handle_command(cmd_key, cmd_value, current_time)

    def generate_states(self) -> Dict[int, Dict[str, Any]]:
        """
        生成每一毫秒的状态数据
        修改：降落完成后继续往后多计算5s（保持运动状态）
        """
        print(f"\n生成状态数据：{self.start_time} - {self.end_time}ms")
        total_points = self.end_time - self.start_time + 1
        print(f"共 {total_points} 个时间点")

        result = {}
        last_progress = 0

        # 遍历每一毫秒
        for t in range(self.start_time, self.end_time + 1):
            # 处理关键帧指令
            for time, commands in self.sorted_keyframes:
                if time == t:
                    print(f"\n>>> 时间 {t}ms 执行指令:")
                    for cmd_key, cmd_value in commands.items():
                        self.parse_command(cmd_key, cmd_value, t)

            # 计算当前位置
            current_pos = self.movement.calculate_position(t)

            # 获取当前灯光状态
            light_state = self.light.get_colors(t)

            # 保存状态
            result[t] = {
                'pos': [round(coord, 2) for coord in current_pos],
                'light': light_state.copy()
            }

            # 显示进度
            progress = int((t - self.start_time) / (self.end_time - self.start_time) * 100)
            if progress >= last_progress + 10:
                print(f"处理进度: {progress}%")
                last_progress = progress

        # 找到最后一个Land指令的时间
        last_land_time = None
        for time, commands in reversed(self.sorted_keyframes):
            if 'Land' in commands:
                last_land_time = time
                break

        if last_land_time is not None:
            # 计算降落完成时间
            land_duration = self.movement.estimated_duration
            land_end_time = last_land_time + int(land_duration * 1000)

            print(f"\n>>> 降落过程: 从{last_land_time}ms开始，需要{land_duration:.2f}s，到{land_end_time}ms结束")

            # 生成降落过程中的状态
            for t in range(last_land_time + 1, land_end_time + 1):
                current_pos = self.movement.calculate_position(t)
                light_state = self.light.get_colors(t)
                result[t] = {
                    'pos': [round(coord, 2) for coord in current_pos],
                    'light': light_state.copy()
                }

            # 降落后再继续计算5000ms（保持运动状态）
            print(f">>> 降落后继续计算5000ms")
            extra_end_time = land_end_time + 5000

            for t in range(land_end_time + 1, extra_end_time + 1):
                # 继续计算位置（保持运动状态）
                current_pos = self.movement.calculate_position(t)
                light_state = self.light.get_colors(t)
                result[t] = {
                    'pos': [round(coord, 2) for coord in current_pos],
                    'light': light_state.copy()
                }

            print(f"   继续计算了 5000ms，到 {extra_end_time}ms 结束")

        else:
            # 如果没有Land指令，在最后一个指令后继续计算5000ms
            print(f"\n>>> 没有降落指令，在最后一个指令后继续计算5000ms")
            last_time = self.end_time
            extra_end_time = last_time + 5000

            for t in range(last_time + 1, extra_end_time + 1):
                # 继续计算位置（保持运动状态）
                current_pos = self.movement.calculate_position(t)
                light_state = self.light.get_colors(t)
                result[t] = {
                    'pos': [round(coord, 2) for coord in current_pos],
                    'light': light_state.copy()
                }

            print(f"   继续计算了 5000ms，到 {extra_end_time}ms 结束")

        print(f"生成完成！总时间点: {len(result)}，最后时间: {max(result.keys())}ms")
        return result


def test_move_command():
    """测试相对移动功能"""
    print("=" * 70)
    print("测试相对移动功能")
    print("=" * 70)

    # 测试数据：先绝对移动，然后相对移动
    test_keyframes = {
        1000: {'TakeOff': 100, 'ZSpeed': [50, 20]},
        3000: {'MoveTo': [200, 200, 100]},  # 绝对移动到(200,200,100)
        5000: {'Move': [50, -50, 0]},  # 相对移动：x+50, y-50, z不变 -> (250,150,100)
        7000: {'Move': [-100, 0, -50]},  # 相对移动：x-100, y不变, z-50 -> (150,150,50)
    }

    takeoff_point = [100, 100]
    interpolator = DroneStateInterpolator(test_keyframes, takeoff_point)
    states = interpolator.generate_states()

    print("\n" + "=" * 100)
    print("时间(ms)   X(cm)    Y(cm)    Z(cm)   Vx(cm/s)  Vy(cm/s)  Vz(cm/s)  状态")
    print("=" * 100)

    key_times = [1000, 2000, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000]

    for t in key_times:
        if t in states:
            pos = states[t]['pos']
            vx = interpolator.movement.current_vx
            vy = interpolator.movement.current_vy
            vz = interpolator.movement.current_vz
            status = "移动中" if interpolator.movement.is_moving else "静止"
            print(
                f"{t:6d}   {pos[0]:6.1f}   {pos[1]:6.1f}   {pos[2]:6.1f}   {vx:6.1f}   {vy:6.1f}   {vz:6.1f}   {status}")


def save_sampled_states(states: Dict[int, Dict[str, Any]], sample_rate: int = 10):
    """
    保存抽样数据到文件，避免文件过大
    :param states: 完整状态数据
    :param sample_rate: 抽样率，每隔sample_rate毫秒保存一个点
    """
    sampled_states = {}
    for t in sorted(states.keys()):
        if t % sample_rate == 0:
            sampled_states[t] = states[t]

    # 确保包含最后一个时间点
    last_time = sorted(states.keys())[-1]
    if last_time not in sampled_states:
        sampled_states[last_time] = states[last_time]

    with open('drone_states_sampled.json', 'w', encoding='utf-8') as f:
        json.dump(sampled_states, f, indent=2)

    print(f"抽样数据已保存到 drone_states_sampled.json (抽样率: 1/{sample_rate})")
    print(f"原始数据点: {len(states)}, 抽样后: {len(sampled_states)}")


def calculateState(takeoff_pos_list, final_dict_list):
    states_list = []
    try:
        os.mkdir('drone_states')
    except:
        pass

    for i in range(len(takeoff_pos_list)):
        interpolator = DroneStateInterpolator(final_dict_list[i], takeoff_pos_list[i])
        states = interpolator.generate_states()
        states_list.append(states)
        with open(f'./drone_states/drone_states_drone{i + 1}.json', "w", encoding='utf-8') as f:
            f.write(json.dumps(states, ensure_ascii=False))
    return states_list


if __name__ == "__main__":
    test_move_command()