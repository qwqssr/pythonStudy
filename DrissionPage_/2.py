import math
import random
import time
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt


@dataclass
class MousePoint:
    """鼠标轨迹点"""
    x: float
    y: float
    timestamp: float
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    acceleration_x: float = 0.0
    acceleration_y: float = 0.0


class HumanMouseSimulator:
    """真实用户鼠标轨迹模拟器"""

    def __init__(self):
        # 人类鼠标移动的基础参数
        self.base_noise_amplitude = 2.0  # 基础噪声幅度
        self.direction_change_probability = 0.15  # 方向改变概率
        self.micro_correction_probability = 0.25  # 微调概率
        self.speed_variation_range = (0.7, 1.4)  # 速度变化范围
        self.max_acceleration = 800  # 最大加速度，避免跳变
        self.min_time_interval = 0.008  # 最小时间间隔(8ms)
        self.max_time_interval = 0.025  # 最大时间间隔(25ms)

        # 人类行为统计参数
        self.avg_speed_range = (150, 400)  # 平均速度范围(像素/秒)
        self.pause_probability = 0.08  # 暂停概率
        self.overshoot_probability = 0.12  # 过冲概率

        # 贝塞尔曲线控制点随机范围
        self.bezier_control_range = 0.3

    def generate_trajectory(self, start_pos: Tuple[float, float],
                            end_pos: Tuple[float, float],
                            duration: Optional[float] = None) -> List[MousePoint]:
        """
        生成从起点到终点的真实用户鼠标轨迹

        Args:
            start_pos: 起始位置 (x, y)
            end_pos: 结束位置 (x, y)
            duration: 预期移动时长，如果为None则自动计算

        Returns:
            鼠标轨迹点列表
        """
        distance = math.sqrt((end_pos[0] - start_pos[0]) ** 2 + (end_pos[1] - start_pos[1]) ** 2)

        if distance < 5:  # 距离太近，直接返回简单轨迹
            return self._generate_short_trajectory(start_pos, end_pos)

        # 计算合理的移动时长
        if duration is None:
            duration = self._calculate_realistic_duration(distance)

        # 生成基础轨迹骨架
        base_points = self._generate_base_trajectory(start_pos, end_pos, duration)

        # 添加人类特征
        human_points = self._add_human_characteristics(base_points)

        # 平滑处理并添加噪声
        smooth_points = self._apply_smoothing_and_noise(human_points)

        # 最终检查和修正
        final_points = self._final_trajectory_validation(smooth_points)

        return final_points

    def _calculate_realistic_duration(self, distance: float) -> float:
        """计算符合人类习惯的移动时长"""
        # 根据Fitts' Law计算基础时长，但加入随机性
        base_speed = random.uniform(*self.avg_speed_range)
        base_duration = distance / base_speed

        # 添加距离相关的修正
        if distance > 500:
            base_duration *= random.uniform(1.1, 1.3)  # 长距离稍慢
        elif distance < 100:
            base_duration *= random.uniform(0.8, 1.0)  # 短距离相对快

        # 添加随机波动
        variation = random.uniform(0.7, 1.4)
        final_duration = base_duration * variation

        # 确保在合理范围内
        return max(0.2, min(final_duration, 3.0))

    def _generate_base_trajectory(self, start_pos: Tuple[float, float],
                                  end_pos: Tuple[float, float],
                                  duration: float) -> List[MousePoint]:
        """生成基础轨迹骨架"""
        points = []

        # 决定轨迹类型
        trajectory_type = self._choose_trajectory_type(start_pos, end_pos)

        if trajectory_type == "bezier":
            points = self._generate_bezier_trajectory(start_pos, end_pos, duration)
        elif trajectory_type == "arc":
            points = self._generate_arc_trajectory(start_pos, end_pos, duration)
        else:  # direct with curves
            points = self._generate_curved_direct_trajectory(start_pos, end_pos, duration)

        return points

    def _choose_trajectory_type(self, start_pos: Tuple[float, float],
                                end_pos: Tuple[float, float]) -> str:
        """选择轨迹类型"""
        distance = math.sqrt((end_pos[0] - start_pos[0]) ** 2 + (end_pos[1] - start_pos[1]) ** 2)

        if distance > 300:
            # 长距离更倾向于使用贝塞尔曲线
            return random.choices(["bezier", "arc", "curved_direct"],
                                  weights=[0.5, 0.3, 0.2])[0]
        else:
            # 短距离更倾向于直接路径但带曲线
            return random.choices(["bezier", "arc", "curved_direct"],
                                  weights=[0.3, 0.2, 0.5])[0]

    def _generate_bezier_trajectory(self, start_pos: Tuple[float, float],
                                    end_pos: Tuple[float, float],
                                    duration: float) -> List[MousePoint]:
        """生成贝塞尔曲线轨迹"""
        # 计算控制点
        mid_x = (start_pos[0] + end_pos[0]) / 2
        mid_y = (start_pos[1] + end_pos[1]) / 2

        # 添加随机偏移到控制点
        distance = math.sqrt((end_pos[0] - start_pos[0]) ** 2 + (end_pos[1] - start_pos[1]) ** 2)
        offset_range = distance * self.bezier_control_range

        control1_x = mid_x + random.uniform(-offset_range, offset_range)
        control1_y = mid_y + random.uniform(-offset_range, offset_range)

        # 有时添加第二个控制点（三次贝塞尔）
        if random.random() < 0.6:
            control2_x = mid_x + random.uniform(-offset_range / 2, offset_range / 2)
            control2_y = mid_y + random.uniform(-offset_range / 2, offset_range / 2)
            return self._cubic_bezier_points(start_pos, (control1_x, control1_y),
                                             (control2_x, control2_y), end_pos, duration)
        else:
            return self._quadratic_bezier_points(start_pos, (control1_x, control1_y),
                                                 end_pos, duration)

    def _generate_arc_trajectory(self, start_pos: Tuple[float, float],
                                 end_pos: Tuple[float, float],
                                 duration: float) -> List[MousePoint]:
        """生成弧形轨迹"""
        points = []

        # 计算弧的参数
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance = math.sqrt(dx ** 2 + dy ** 2)

        # 弧度和半径
        arc_height = random.uniform(distance * 0.1, distance * 0.3)
        if random.random() < 0.5:
            arc_height = -arc_height  # 反向弧

        # 计算时间间隔
        num_points = int(duration / random.uniform(self.min_time_interval, self.max_time_interval))
        num_points = max(10, min(num_points, 100))

        current_time = time.time()

        for i in range(num_points + 1):
            t = i / num_points

            # 计算弧上的点
            mid_x = start_pos[0] + dx * t
            mid_y = start_pos[1] + dy * t

            # 添加弧形偏移
            arc_offset = arc_height * math.sin(math.pi * t)

            # 垂直方向的偏移
            if abs(dx) > abs(dy):
                x = mid_x
                y = mid_y + arc_offset
            else:
                x = mid_x + arc_offset
                y = mid_y

            timestamp = current_time + t * duration
            points.append(MousePoint(x, y, timestamp))

        return points

    def _generate_curved_direct_trajectory(self, start_pos: Tuple[float, float],
                                           end_pos: Tuple[float, float],
                                           duration: float) -> List[MousePoint]:
        """生成带曲线的直接轨迹"""
        points = []

        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]

        num_points = int(duration / random.uniform(self.min_time_interval, self.max_time_interval))
        num_points = max(10, min(num_points, 100))

        current_time = time.time()

        for i in range(num_points + 1):
            t = i / num_points

            # 非线性时间函数，模拟加速和减速
            eased_t = self._ease_in_out_cubic(t)

            x = start_pos[0] + dx * eased_t
            y = start_pos[1] + dy * eased_t

            timestamp = current_time + t * duration
            points.append(MousePoint(x, y, timestamp))

        return points

    def _quadratic_bezier_points(self, p0: Tuple[float, float],
                                 p1: Tuple[float, float],
                                 p2: Tuple[float, float],
                                 duration: float) -> List[MousePoint]:
        """生成二次贝塞尔曲线点"""
        points = []
        num_points = int(duration / random.uniform(self.min_time_interval, self.max_time_interval))
        num_points = max(10, min(num_points, 100))

        current_time = time.time()

        for i in range(num_points + 1):
            t = i / num_points

            # 二次贝塞尔公式
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]

            timestamp = current_time + t * duration
            points.append(MousePoint(x, y, timestamp))

        return points

    def _cubic_bezier_points(self, p0: Tuple[float, float],
                             p1: Tuple[float, float],
                             p2: Tuple[float, float],
                             p3: Tuple[float, float],
                             duration: float) -> List[MousePoint]:
        """生成三次贝塞尔曲线点"""
        points = []
        num_points = int(duration / random.uniform(self.min_time_interval, self.max_time_interval))
        num_points = max(10, min(num_points, 100))

        current_time = time.time()

        for i in range(num_points + 1):
            t = i / num_points

            # 三次贝塞尔公式
            x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0]
            y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]

            timestamp = current_time + t * duration
            points.append(MousePoint(x, y, timestamp))

        return points

    def _add_human_characteristics(self, points: List[MousePoint]) -> List[MousePoint]:
        """添加人类特征"""
        if len(points) < 3:
            return points

        enhanced_points = []

        for i, point in enumerate(points):
            new_point = MousePoint(point.x, point.y, point.timestamp)

            # 添加微调动作
            if random.random() < self.micro_correction_probability:
                correction_x = random.uniform(-3, 3)
                correction_y = random.uniform(-3, 3)
                new_point.x += correction_x
                new_point.y += correction_y

            # 添加随机暂停
            if random.random() < self.pause_probability and i > 0:
                pause_duration = random.uniform(0.05, 0.2)
                new_point.timestamp += pause_duration

            # 方向微调
            if i > 0 and random.random() < self.direction_change_probability:
                angle_change = random.uniform(-0.2, 0.2)  # 弧度
                dx = new_point.x - points[i - 1].x
                dy = new_point.y - points[i - 1].y

                cos_a = math.cos(angle_change)
                sin_a = math.sin(angle_change)

                new_dx = dx * cos_a - dy * sin_a
                new_dy = dx * sin_a + dy * cos_a

                new_point.x = points[i - 1].x + new_dx
                new_point.y = points[i - 1].y + new_dy

            enhanced_points.append(new_point)

        # 添加过冲效果
        if random.random() < self.overshoot_probability and len(enhanced_points) > 1:
            enhanced_points = self._add_overshoot(enhanced_points)

        return enhanced_points

    def _add_overshoot(self, points: List[MousePoint]) -> List[MousePoint]:
        """添加过冲效果（人类经常超过目标然后回调）"""
        if len(points) < 5:
            return points

        # 在轨迹末尾添加过冲
        target = points[-1]
        pre_target = points[-2]

        dx = target.x - pre_target.x
        dy = target.y - pre_target.y

        # 过冲距离
        overshoot_distance = random.uniform(5, 15)
        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance > 0:
            overshoot_x = target.x + (dx / distance) * overshoot_distance
            overshoot_y = target.y + (dy / distance) * overshoot_distance

            # 添加过冲点
            overshoot_point = MousePoint(
                overshoot_x, overshoot_y,
                target.timestamp + random.uniform(0.05, 0.1)
            )

            # 添加回调点
            correction_point = MousePoint(
                target.x + random.uniform(-2, 2),
                target.y + random.uniform(-2, 2),
                overshoot_point.timestamp + random.uniform(0.1, 0.2)
            )

            points.append(overshoot_point)
            points.append(correction_point)

        return points

    def _apply_smoothing_and_noise(self, points: List[MousePoint]) -> List[MousePoint]:
        """应用平滑处理和噪声"""
        if len(points) < 3:
            return points

        # 计算速度和加速度
        for i in range(1, len(points)):
            dt = points[i].timestamp - points[i - 1].timestamp
            if dt > 0:
                points[i].velocity_x = (points[i].x - points[i - 1].x) / dt
                points[i].velocity_y = (points[i].y - points[i - 1].y) / dt

        for i in range(2, len(points)):
            dt = points[i].timestamp - points[i - 1].timestamp
            if dt > 0:
                points[i].acceleration_x = (points[i].velocity_x - points[i - 1].velocity_x) / dt
                points[i].acceleration_y = (points[i].velocity_y - points[i - 1].velocity_y) / dt

        # 添加自然噪声
        for i, point in enumerate(points):
            if i > 0:  # 不修改起点
                # 基于速度的自适应噪声
                speed = math.sqrt(point.velocity_x ** 2 + point.velocity_y ** 2)
                noise_factor = max(0.5, min(2.0, speed / 200))  # 速度越快噪声越大

                noise_x = random.gauss(0, self.base_noise_amplitude * noise_factor)
                noise_y = random.gauss(0, self.base_noise_amplitude * noise_factor)

                point.x += noise_x
                point.y += noise_y

        return points

    def _final_trajectory_validation(self, points: List[MousePoint]) -> List[MousePoint]:
        """最终轨迹验证和修正"""
        if len(points) < 2:
            return points

        validated_points = [points[0]]  # 保留起点

        for i in range(1, len(points)):
            current = points[i]
            previous = validated_points[-1]

            # 检查时间间隔
            dt = current.timestamp - previous.timestamp
            if dt < self.min_time_interval:
                # 时间间隔太小，调整时间戳
                current.timestamp = previous.timestamp + self.min_time_interval
            elif dt > self.max_time_interval * 3:
                # 时间间隔太大，插入中间点
                self._insert_intermediate_points(validated_points, previous, current)
                continue

            # 检查加速度
            if abs(current.acceleration_x) > self.max_acceleration or abs(
                    current.acceleration_y) > self.max_acceleration:
                # 加速度太大，平滑处理
                current.x = (current.x + previous.x) / 2
                current.y = (current.y + previous.y) / 2

            validated_points.append(current)

        return validated_points

    def _insert_intermediate_points(self, validated_points: List[MousePoint],
                                    start: MousePoint, end: MousePoint):
        """在两点间插入中间点"""
        num_intermediate = int((end.timestamp - start.timestamp) / self.max_time_interval)

        for i in range(1, num_intermediate + 1):
            t = i / (num_intermediate + 1)

            intermediate_x = start.x + (end.x - start.x) * t
            intermediate_y = start.y + (end.y - start.y) * t
            intermediate_time = start.timestamp + (end.timestamp - start.timestamp) * t

            # 添加轻微随机变化
            intermediate_x += random.uniform(-1, 1)
            intermediate_y += random.uniform(-1, 1)

            intermediate_point = MousePoint(intermediate_x, intermediate_y, intermediate_time)
            validated_points.append(intermediate_point)

    def _generate_short_trajectory(self, start_pos: Tuple[float, float],
                                   end_pos: Tuple[float, float]) -> List[MousePoint]:
        """生成短距离轨迹"""
        current_time = time.time()
        points = [
            MousePoint(start_pos[0], start_pos[1], current_time),
            MousePoint(end_pos[0] + random.uniform(-1, 1),
                       end_pos[1] + random.uniform(-1, 1),
                       current_time + random.uniform(0.1, 0.3))
        ]
        return points

    def _ease_in_out_cubic(self, t: float) -> float:
        """三次缓动函数"""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return (t - 1) * (2 * t - 2) * (2 * t - 2) + 1

    def visualize_trajectory(self, points: List[MousePoint], title: str = "Mouse Trajectory"):
        """可视化轨迹"""
        if len(points) < 2:
            return

        x_coords = [p.x for p in points]
        y_coords = [p.y for p in points]

        plt.figure(figsize=(12, 8))

        # 绘制轨迹
        plt.subplot(2, 2, 1)
        plt.plot(x_coords, y_coords, 'b-', alpha=0.7, linewidth=1)
        plt.scatter(x_coords[0], y_coords[0], c='green', s=100, label='Start')
        plt.scatter(x_coords[-1], y_coords[-1], c='red', s=100, label='End')
        plt.title(f'{title} - Path')
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # 绘制X坐标时间序列
        times = [(p.timestamp - points[0].timestamp) for p in points]
        plt.subplot(2, 2, 2)
        plt.plot(times, x_coords, 'r-', alpha=0.7)
        plt.title('X Coordinate over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('X')
        plt.grid(True, alpha=0.3)

        # 绘制Y坐标时间序列
        plt.subplot(2, 2, 3)
        plt.plot(times, y_coords, 'g-', alpha=0.7)
        plt.title('Y Coordinate over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('Y')
        plt.grid(True, alpha=0.3)

        # 绘制速度
        if len(points) > 1:
            speeds = [math.sqrt(p.velocity_x ** 2 + p.velocity_y ** 2) for p in points[1:]]
            plt.subplot(2, 2, 4)
            plt.plot(times[1:], speeds, 'm-', alpha=0.7)
            plt.title('Speed over Time')
            plt.xlabel('Time (s)')
            plt.ylabel('Speed (px/s)')
            plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()


# 使用示例和测试
if __name__ == "__main__":
    simulator = HumanMouseSimulator()

    # 用户输入坐标（示例坐标）
    start_pos = (100, 100)  # 起始坐标
    end_pos = (300, 300)    # 目标坐标

    # 生成轨迹
    print(f"生成轨迹: {start_pos} → {end_pos}")
    points = simulator.generate_trajectory(start_pos, end_pos)

    # 打印基础信息
    print(f"轨迹点数: {len(points)}")
    if len(points) > 1:
        total_time = points[-1].timestamp - points[0].timestamp
        distance = math.hypot(end_pos[0]-start_pos[0], end_pos[1]-start_pos[1])
        avg_speed = distance / total_time if total_time > 0 else 0
        print(f"移动距离: {distance:.1f}px")
        print(f"总时长: {total_time:.3f}s")
        print(f"平均速度: {avg_speed:.1f}px/s")

    # 打印详细轨迹点数据
    print("\n轨迹点详细信息：")
    print(f"{'序号':<5} | {'X':<8} | {'Y':<8} | {'时间(s)':<8} | {'速度(px/s)':<15} | {'加速度(px/s²)':<15}")
    print("-" * 75)
    for i, p in enumerate(points):
        time_offset = p.timestamp - points[0].timestamp
        speed = math.hypot(p.velocity_x, p.velocity_y) if i > 0 else 0
        acceleration = math.hypot(p.acceleration_x, p.acceleration_y) if i > 1 else 0
        print(
            f"{i+1:<5} | {p.x:8.2f} | {p.y:8.2f} | {time_offset:8.3f} | "
            f"{speed:15.2f} | {acceleration:15.2f}"
        )

    # 可视化轨迹
    simulator.visualize_trajectory(points, "自定义轨迹")