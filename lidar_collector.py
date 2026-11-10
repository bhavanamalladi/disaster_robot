"""
Edge Cloud - Multi-Robot LiDAR Data Collector

Features:
1. Multi-robot LiDAR subscriptions
2. Sensor data validation
3. Invalid measurement rejection
4. Local database storage
5. Missing sensor data detection
6. Sensor communication recovery
7. Database error handling
"""

import math
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

from database import initialize_database, save_lidar_observation


class LidarCollector(Node):

    def __init__(self):
        super().__init__('edge_lidar_collector')

        # Initialize database
        initialize_database()

        # Robot LiDAR topics
        self.robot_topics = {
            'reference_ugv': '/scan',
            'robot_2': '/robot2/scan',
        }

        # Message counters
        self.message_counts = {
            robot_id: 0
            for robot_id in self.robot_topics
        }

        # Last received message timestamps
        self.last_message_time = {
            robot_id: None
            for robot_id in self.robot_topics
        }

        # Track sensor communication status
        self.sensor_status = {
            robot_id: 'WAITING'
            for robot_id in self.robot_topics
        }

        # Maximum allowed time without sensor data
        self.SENSOR_TIMEOUT = 5.0

        # ROS subscriptions
        self.robot_subscriptions = []

        for robot_id, topic in self.robot_topics.items():

            subscription = self.create_subscription(
                LaserScan,
                topic,
                lambda msg, rid=robot_id: self.lidar_callback(
                    msg, rid
                ),
                10
            )

            self.robot_subscriptions.append(subscription)

            self.get_logger().info(
                f'Subscribed to {topic} for {robot_id}'
            )

        # Start sensor watchdog
        self.watchdog_timer = self.create_timer(
            1.0,
            self.check_sensor_status
        )

        self.get_logger().info(
            'Multi-Robot Edge Cloud LiDAR Collector started.'
        )

    # --------------------------------------------------
    # LIDAR CALLBACK
    # --------------------------------------------------

    def lidar_callback(self, msg, robot_id):
        """Process and store incoming LiDAR measurements."""

        try:

            self.message_counts[robot_id] += 1

            self.last_message_time[robot_id] = time.monotonic()

            # Detect sensor recovery
            if self.sensor_status[robot_id] != 'ONLINE':

                self.sensor_status[robot_id] = 'ONLINE'

                self.get_logger().info(
                    f'{robot_id}: LiDAR communication restored.'
                )

            # Validate sensor range limits
            if (
                not math.isfinite(msg.range_min)
                or not math.isfinite(msg.range_max)
                or msg.range_min < 0
                or msg.range_max <= msg.range_min
            ):

                self.get_logger().warning(
                    f'{robot_id}: Invalid LiDAR range limits.'
                )

                return

            # Filter valid measurements
            valid_ranges = [

                distance

                for distance in msg.ranges

                if math.isfinite(distance)

                and msg.range_min <= distance <= msg.range_max
            ]

            # Reject empty or invalid readings
            if not valid_ranges:

                self.get_logger().warning(
                    f'{robot_id}: No valid LiDAR measurements.'
                )

                return

            nearest_distance = min(valid_ranges)

            # Save observation locally
            save_lidar_observation(

                robot_id=robot_id,

                total_measurements=len(msg.ranges),

                valid_measurements=len(valid_ranges),

                nearest_distance=nearest_distance
            )

            self.get_logger().info(

                f'Robot: {robot_id} | '

                f'Message: {self.message_counts[robot_id]} | '

                f'Total: {len(msg.ranges)} | '

                f'Valid: {len(valid_ranges)} | '

                f'Nearest obstacle: {nearest_distance:.2f} m | '

                f'Saved to database'
            )

        except Exception as error:

            self.get_logger().error(
                f'LiDAR processing error for {robot_id}: {error}'
            )

    # --------------------------------------------------
    # SENSOR WATCHDOG
    # --------------------------------------------------

    def check_sensor_status(self):
        """Detect missing LiDAR messages from robots."""

        current_time = time.monotonic()

        for robot_id in self.robot_topics:

            last_time = self.last_message_time[robot_id]

            if last_time is None:

                if self.sensor_status[robot_id] != 'OFFLINE':

                    self.sensor_status[robot_id] = 'OFFLINE'

                    self.get_logger().warning(
                        f'{robot_id}: Waiting for LiDAR data. '
                        f'No messages received yet.'
                    )

                continue

            elapsed_time = current_time - last_time

            if elapsed_time > self.SENSOR_TIMEOUT:

                if self.sensor_status[robot_id] != 'OFFLINE':

                    self.sensor_status[robot_id] = 'OFFLINE'

                    self.get_logger().error(

                        f'WARNING: {robot_id} LiDAR data '
                        f'has stopped arriving! '

                        f'Last message: {elapsed_time:.2f} seconds ago.'
                    )

            else:

                if self.sensor_status[robot_id] == 'OFFLINE':

                    self.sensor_status[robot_id] = 'ONLINE'

                    self.get_logger().info(
                        f'{robot_id}: LiDAR communication recovered.'
                    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main(args=None):

    rclpy.init(args=args)

    node = None

    try:

        node = LidarCollector()

        rclpy.spin(node)

    except KeyboardInterrupt:

        print('LiDAR Collector stopped.')

    except Exception as error:

        print(f'Edge Cloud collector error: {error}')

        raise

    finally:

        if node is not None:

            node.destroy_node()

        if rclpy.ok():

            rclpy.shutdown()


if __name__ == '__main__':

    main()