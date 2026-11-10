import rclpy
from rclpy.node import Node

from nav_msgs.msg import OccupancyGrid
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

import math


class MapFusion(Node):

    def __init__(self):
        super().__init__('map_fusion')

        self.robot1_map = None
        self.robot2_map = None

        # Initial relative transformation
        self.robot2_offset_x = 0.0
        self.robot2_offset_y = 0.0

        self.qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=10
        )

        self.subscription1 = self.create_subscription(
            OccupancyGrid,
            '/map',
            self.robot1_callback,
            self.qos
        )

        self.subscription2 = self.create_subscription(
            OccupancyGrid,
            '/robot2/map',
            self.robot2_callback,
            self.qos
        )

        self.publisher = self.create_publisher(
            OccupancyGrid,
            '/edge_cloud/fused_map',
            self.qos
        )

        self.timer = self.create_timer(2.0, self.fuse_maps)

        self.get_logger().info('Edge Cloud Map Fusion initialized.')

    def robot1_callback(self, msg):
        self.robot1_map = msg

    def robot2_callback(self, msg):
        self.robot2_map = msg

    def fuse_maps(self):

        if self.robot1_map is None or self.robot2_map is None:
            return

        map1 = self.robot1_map
        map2 = self.robot2_map

        resolution = map1.info.resolution

        if not math.isclose(
            resolution,
            map2.info.resolution,
            rel_tol=1e-5
        ):
            self.get_logger().error('Map resolutions do not match.')
            return

        if map1.info.width == 0 or map1.info.height == 0:
            return

        if map2.info.width == 0 or map2.info.height == 0:
            return

        # Check map orientation
        q1 = map1.info.origin.orientation
        q2 = map2.info.origin.orientation

        if not (
            math.isclose(q1.z, q2.z, abs_tol=1e-5)
            and math.isclose(q1.w, q2.w, abs_tol=1e-5)
        ):
            self.get_logger().error(
                'Map orientations differ. Alignment required.'
            )
            return

        # Calculate transformed Robot 2 origin
        origin1_x = map1.info.origin.position.x
        origin1_y = map1.info.origin.position.y

        origin2_x = (
            map2.info.origin.position.x + self.robot2_offset_x
        )

        origin2_y = (
            map2.info.origin.position.y + self.robot2_offset_y
        )

        # Calculate combined map boundaries
        min_x = min(origin1_x, origin2_x)
        min_y = min(origin1_y, origin2_y)

        max_x = max(
            origin1_x + map1.info.width * resolution,
            origin2_x + map2.info.width * resolution
        )

        max_y = max(
            origin1_y + map1.info.height * resolution,
            origin2_y + map2.info.height * resolution
        )

        width = math.ceil((max_x - min_x) / resolution)
        height = math.ceil((max_y - min_y) / resolution)

        fused_data = [-1] * (width * height)

        def merge_grid(source_map, transformed_origin_x,
                       transformed_origin_y):

            for row in range(source_map.info.height):

                for col in range(source_map.info.width):

                    source_index = (
                        row * source_map.info.width + col
                    )

                    value = source_map.data[source_index]

                    if value < 0:
                        continue

                    world_x = (
                        transformed_origin_x
                        + col * resolution
                    )

                    world_y = (
                        transformed_origin_y
                        + row * resolution
                    )

                    target_col = round(
                        (world_x - min_x) / resolution
                    )

                    target_row = round(
                        (world_y - min_y) / resolution
                    )

                    if not (
                        0 <= target_col < width
                        and 0 <= target_row < height
                    ):
                        continue

                    target_index = (
                        target_row * width + target_col
                    )

                    existing = fused_data[target_index]

                    if value >= 65:
                        fused_data[target_index] = 100

                    elif value >= 0 and existing == -1:
                        fused_data[target_index] = value

        # Merge Robot 1
        merge_grid(map1, origin1_x, origin1_y)

        # Merge Robot 2 after coordinate translation
        merge_grid(map2, origin2_x, origin2_y)

        # Construct fused OccupancyGrid
        fused_map = OccupancyGrid()

        fused_map.header.stamp = self.get_clock().now().to_msg()
        fused_map.header.frame_id = 'map'

        fused_map.info.resolution = resolution
        fused_map.info.width = width
        fused_map.info.height = height

        fused_map.info.origin.position.x = min_x
        fused_map.info.origin.position.y = min_y
        fused_map.info.origin.position.z = 0.0

        fused_map.info.origin.orientation = map1.info.origin.orientation

        fused_map.data = fused_data

        self.publisher.publish(fused_map)

        self.get_logger().info(
            f'Fused map published: {width} x {height}'
        )


def main(args=None):

    rclpy.init(args=args)

    node = MapFusion()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
