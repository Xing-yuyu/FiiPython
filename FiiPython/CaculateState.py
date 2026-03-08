# CaculateState.py (添加相对移动功能)
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
    """跑马灯效果：四个马达依次变色"""

    def __init__(self, start_time: int, colors: List[Tuple[int, int, int]],
                 clock: bool, delay: int):
        super().__init__(start_time)
        self.colors = colors
        self.clock = clock  # True:顺时针, False:逆时针
        self.delay = delay
        self.num_colors = len(colors)

    def get_motor_colors(self, current_time: int) -> Dict[int, Tuple[int, int, int]]:
        time_offset = (current_time - self.start_time) // self.delay
        phase = time_offset % self.num_colors

        result = {}
        if self.clock:  # 顺时针: 1->2->3->4
            for i in range(4):
                color_index = (phase + i) % self.num_colors
                result[i + 1] = self.colors[color_index]
        else:  # 逆时针: 4->3->2->1
            for i in range(4):
                color_index = (phase + (3 - i)) % self.num_colors
                result[i + 1] = self.colors[color_index]

        return result


class MovementState:
    """运动状态 - 单位：厘米(cm)"""

    def __init__(self, takeoff_pos: List[float]):
        """
        :param takeoff_pos: 起飞点坐标 [x, y] (cm)
        """
        self.takeoff_pos = takeoff_pos  # 起飞点
        self.pos = [takeoff_pos[0], takeoff_pos[1], 0.0]  # 当前位置
        self.target_pos = [takeoff_pos[0], takeoff_pos[1], 0.0]  # 目标位置

        # 默认速度 [速度(cm/s), 加速度(cm/s²)]
        self.xy_speed = [100.0, 100.0]  # [速度, 加速度]
        self.z_speed = [100.0, 100.0]  # [速度, 加速度]

        self.is_flying = False  # 是否在飞行中

        # 运动状态
        self.start_move_time = 0  # 开始移动的时间(ms)
        self.start_pos = [takeoff_pos[0], takeoff_pos[1], 0.0]  # 开始移动的位置

        # 当前运动的速度 (cm/s) - 用于连续运动
        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_vz = 0.0

        # 运动参数 - 简化为每个轴的目标速度和加速度
        self.target_vx = 0.0
        self.target_vy = 0.0
        self.target_vz = 0.0
        self.accel_x = 0.0
        self.accel_y = 0.0
        self.accel_z = 0.0

        self.estimated_duration = 0  # 预计移动总时间 (s)
        self.estimated_end_time = 0  # 预计结束时间 (ms)
        self.last_command_time = 0  # 最后指令时间

        # 运动标志
        self.is_moving = False

    def _get_current_velocity(self) -> Tuple[float, float, float]:
        """获取当前时刻的实际速度"""
        return (self.current_vx, self.current_vy, self.current_vz)

    def takeoff(self, height: float, current_time: int):
        """起飞到指定高度"""
        self.is_flying = True
        self.is_moving = True

        # 记录开始运动时的状态
        self.start_move_time = current_time
        self.start_pos = self.pos.copy()
        self.target_pos = [self.takeoff_pos[0], self.takeoff_pos[1], height]

        # 设置运动参数
        distance = height - self.pos[2]
        direction = 1 if distance > 0 else -1

        # 目标速度（最大速度）
        self.target_vz = self.z_speed[0] * direction
        # 加速度
        self.accel_z = self.z_speed[1] * direction

        # 估算时间
        abs_distance = abs(distance)
        v_max = self.z_speed[0]
        a = self.z_speed[1]

        if a > 0:
            # 加速到最大速度所需距离
            accel_dist = v_max * v_max / (2 * a)
            if abs_distance <= 2 * accel_dist:
                # 三角形速度曲线
                v_peak = math.sqrt(a * abs_distance)
                self.estimated_duration = 2 * v_peak / a
            else:
                # 梯形速度曲线
                accel_time = v_max / a
                const_dist = abs_distance - 2 * accel_dist
                const_time = const_dist / v_max
                self.estimated_duration = 2 * accel_time + const_time
        else:
            self.estimated_duration = abs_distance / v_max if v_max > 0 else 0

        self.estimated_end_time = current_time + int(self.estimated_duration * 1000)

        print(f"  起飞: 从{self.start_pos}到{self.target_pos}, 需要{self.estimated_duration:.2f}s")

    def land(self, current_time: int):
        """降落 - 有运动过程"""
        if self.pos[2] <= 0:
            print(f"  已经在 ground")
            return

        self.is_moving = True
        self.start_move_time = current_time
        self.start_pos = self.pos.copy()
        self.target_pos = [self.pos[0], self.pos[1], 0.0]

        # 设置运动参数（减速下降）
        distance = -self.pos[2]  # 负数
        direction = -1  # 向下

        # 目标速度（负值表示向下）
        self.target_vz = -self.z_speed[0]
        # 加速度（负值表示减速）
        self.accel_z = -self.z_speed[1]

        # 估算时间
        abs_distance = self.pos[2]
        v_max = self.z_speed[0]
        a = self.z_speed[1]

        if a > 0:
            # 减速到0所需距离
            decel_dist = v_max * v_max / (2 * a)
            if abs_distance <= decel_dist:
                # 直接减速
                self.estimated_duration = v_max / a
            else:
                # 匀速然后减速
                const_dist = abs_distance - decel_dist
                const_time = const_dist / v_max
                decel_time = v_max / a
                self.estimated_duration = const_time + decel_time
        else:
            self.estimated_duration = abs_distance / v_max if v_max > 0 else 0

        self.estimated_end_time = current_time + int(self.estimated_duration * 1000)

        print(f"  降落: 从高度{self.pos[2]:.1f}cm到地面, 需要{self.estimated_duration:.2f}s")

    def move_to(self, target: List[float], current_time: int):
        """移动到目标点（绝对移动）"""
        self.is_moving = True
        self.start_move_time = current_time
        self.start_pos = self.pos.copy()
        self.target_pos = target

        # 计算各轴位移
        dx = target[0] - self.pos[0]
        dy = target[1] - self.pos[1]
        dz = target[2] - self.pos[2]

        print(f"  绝对移动: 从{self.start_pos}到{self.target_pos}")
        print(f"        当前速度: vx={self.current_vx:.1f}, vy={self.current_vy:.1f}, vz={self.current_vz:.1f}")

        # 计算各轴的目标速度和加速度
        # 对于有位移的轴，设置目标速度
        if abs(dx) > 0.001:
            self.target_vx = self.xy_speed[0] if dx > 0 else -self.xy_speed[0]
            self.accel_x = self.xy_speed[1] if dx > 0 else -self.xy_speed[1]
        else:
            self.target_vx = 0
            self.accel_x = 0

        if abs(dy) > 0.001:
            self.target_vy = self.xy_speed[0] if dy > 0 else -self.xy_speed[0]
            self.accel_y = self.xy_speed[1] if dy > 0 else -self.xy_speed[1]
        else:
            self.target_vy = 0
            self.accel_y = 0

        if abs(dz) > 0.001:
            self.target_vz = self.z_speed[0] if dz > 0 else -self.z_speed[0]
            self.accel_z = self.z_speed[1] if dz > 0 else -self.z_speed[1]
        else:
            self.target_vz = 0
            self.accel_z = 0

        # 估算各轴所需时间（简单估算）
        time_x = abs(dx) / self.xy_speed[0] if abs(dx) > 0.001 else 0
        time_y = abs(dy) / self.xy_speed[0] if abs(dy) > 0.001 else 0
        time_z = abs(dz) / self.z_speed[0] if abs(dz) > 0.001 else 0

        self.estimated_duration = max(time_x, time_y, time_z)
        if self.estimated_duration <= 0:
            self.estimated_duration = 0.001

        self.estimated_end_time = current_time + int(self.estimated_duration * 1000)

        print(f"        目标速度: vx={self.target_vx:.1f}, vy={self.target_vy:.1f}, vz={self.target_vz:.1f}")
        print(f"        总时间: {self.estimated_duration:.2f}s")

        self.last_command_time = current_time

    def move(self, offset: List[float], current_time: int):
        """
        相对移动 - 从当前位置移动指定的偏移量

        Args:
            offset: 相对偏移量 [dx, dy, dz] (整数，可正可负)
            current_time: 当前时间戳
        """
        # 计算目标位置 = 当前位置 + 偏移量
        target = [
            self.pos[0] + offset[0],
            self.pos[1] + offset[1],
            self.pos[2] + offset[2]
        ]

        print(f"  相对移动: 偏移{offset} -> 目标位置{target}")

        # 调用绝对移动逻辑
        self.move_to(target, current_time)

    def calculate_position(self, current_time: int) -> List[float]:
        """
        根据简化的运动学公式计算当前位置
        使用速度控制，避免复杂的二次方程
        """
        dt = (current_time - self.start_move_time) / 1000.0

        # 如果还没开始移动，返回起始位置
        if dt <= 0:
            return self.pos.copy()

        # 计算运动进度
        progress = min(1.0, dt / self.estimated_duration) if self.estimated_duration > 0 else 1.0

        # 简单的线性插值（但保留速度信息用于连续运动）
        if progress < 1.0:
            # 位置：起始位置 + 进度 * 位移
            x = self.start_pos[0] + (self.target_pos[0] - self.start_pos[0]) * progress
            y = self.start_pos[1] + (self.target_pos[1] - self.start_pos[1]) * progress
            z = self.start_pos[2] + (self.target_pos[2] - self.start_pos[2]) * progress

            # 速度：基于目标速度的简单估算
            self.current_vx = self.target_vx * (1 - progress) if abs(self.target_vx) > 0 else 0
            self.current_vy = self.target_vy * (1 - progress) if abs(self.target_vy) > 0 else 0
            self.current_vz = self.target_vz * (1 - progress) if abs(self.target_vz) > 0 else 0
        else:
            # 到达目标
            x, y, z = self.target_pos
            self.current_vx = 0
            self.current_vy = 0
            self.current_vz = 0
            self.is_moving = False
            if self.target_pos[2] == 0:
                self.is_flying = False

        self.pos = [x, y, z]
        return [x, y, z]

    def update_speed(self, xy_speed: List[float] = None, z_speed: List[float] = None):
        """更新速度设置"""
        if xy_speed:
            self.xy_speed = xy_speed
        if z_speed:
            self.z_speed = z_speed


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
            effect = MotorHorseEffect(
                current_time,
                cmd_value['colors'],
                cmd_value['clock'],
                cmd_value['delay']
            )
            self.motor_horse_effect = effect
            # 清除单独的马达效果
            for i in range(1, 5):
                self.motor_effects[i] = None
            direction = "顺时针" if cmd_value['clock'] else "逆时针"
            print(f"  灯光: 跑马灯 {direction}, delay={cmd_value['delay']}ms")

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

        # 处理跑马灯效果
        if self.motor_horse_effect:
            motor_colors = self.motor_horse_effect.get_motor_colors(current_time)
            for motor, color in motor_colors.items():
                result[f'motor{motor}'] = color
        else:
            # 处理单独的马达
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

        self.keyframes = dict(input_keyframes)
        self.sorted_keyframes = sorted(self.keyframes.items())
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

            # 降落后再延长5000ms
            print(f">>> 降落完成后延长5000ms")
            last_time = land_end_time
            last_state = result[last_time]

            for t in range(last_time + 1, last_time + 5001):
                result[t] = {
                    'pos': [last_state['pos'][0], last_state['pos'][1], 0.0],
                    'light': last_state['light'].copy()
                }
        else:
            # 如果没有Land指令，只延长5000ms
            print(f"\n>>> 延长5000ms")
            last_time = self.end_time
            last_state = result[last_time]

            for t in range(last_time + 1, last_time + 5001):
                result[t] = {
                    'pos': [last_state['pos'][0], last_state['pos'][1], last_state['pos'][2]],
                    'light': last_state['light'].copy()
                }

        print(f"生成完成！总时间点: {len(result)}")
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


def caculateState(takeoff_pos_list, final_dict_list):
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