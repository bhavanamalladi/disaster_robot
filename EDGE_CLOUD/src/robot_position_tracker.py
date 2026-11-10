import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import sys
import os

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)))
)

import database


class RobotPositionTracker(Node):

    def update_position(self, robot_id, msg):

        """Track local and estimated Gazebo world coordinates."""

        # Extract local odometry position
        local_x = msg.pose.pose.position.x
        local_y = msg.pose.pose.position.y
        local_z = msg.pose.pose.position.z

        # Get initial Gazebo world position
        initial = self.robot_initial_positions[robot_id]

        # Calculate estimated world position
        world_x = local_x + initial['x']
        world_y = local_y + initial['y']

        # Store both coordinate systems
        self.robot_positions[robot_id] = {
            'local_x': local_x,
            'local_y': local_y,
            'world_x': world_x,
            'world_y': world_y,
            'z': local_z
        }

        # Save the latest position to the Edge Cloud database
        database.save_robot_position(
            robot_id,
            world_x,
            world_y,
            local_z
        )

        self.get_logger().info(
            f'{robot_id} | '
            f'World X={world_x:.2f}, '
            f'World Y={world_y:.2f}'
        )    

    def __init__(self):
        super().__init__('robot_position_tracker')

        # Store the latest positions of both robots
        self.robot_positions = {
            'reference_ugv': None,
            'robot_2': None
        }

        # Initial Gazebo world positions
        self.robot_initial_positions = {
            'reference_ugv': {'x': 0.0, 'y': 0.0},
            'robot_2': {'x': 2.0, 'y': 0.0}
        }

        # Robot 1 odometry subscription
        self.robot1_subscription = self.create_subscription(
            Odometry,
            '/model/reference_ugv/odometry',
            lambda msg: self.update_position('reference_ugv', msg),
            10
        )

        # Robot 2 odometry subscription
        self.robot2_subscription = self.create_subscription(
            Odometry,
            '/model/robot_2/odometry',
            lambda msg: self.update_position('robot_2', msg),
            10
        )

        self.get_logger().info(
            'Robot Position Tracker initialized.'
        )

def main(args=None):

    rclpy.init(args=args)

    node = RobotPositionTracker()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()