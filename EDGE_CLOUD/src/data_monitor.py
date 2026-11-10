"""
Edge Cloud - Data Monitor
Summarizes locally stored LiDAR observations.
"""

from database import get_recent_observations, DATABASE_PATH
import sqlite3


def display_summary():
    """Display a summary of stored LiDAR observations."""

    with sqlite3.connect(DATABASE_PATH) as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM lidar_observations"
        ).fetchone()[0]

        stats = connection.execute("""
            SELECT
                COUNT(nearest_distance),
                MIN(nearest_distance),
                AVG(nearest_distance)
            FROM lidar_observations
        """).fetchone()

        robot_ids = connection.execute("""
            SELECT DISTINCT robot_id
            FROM lidar_observations
        """).fetchall()

    print("\n" + "=" * 50)
    print("       EDGE CLOUD DATA MONITOR")
    print("=" * 50)

    print(f"Database: {DATABASE_PATH}")
    print(f"Total observations: {total}")
    print(f"Observations with distances: {stats[0]}")

    if stats[0] > 0:
        print(f"Minimum recorded distance: {stats[1]:.2f} m")
        print(f"Average recorded distance: {stats[2]:.2f} m")

    print("Robots recorded:", ", ".join(row[0] for row in robot_ids)
          if robot_ids else "None")

    print("\nLatest 5 observations:")

    recent = get_recent_observations(5)

    if not recent:
        print("No observations stored yet.")
    else:
        for observation in recent:
            print(
                f"ID: {observation['id']} | "
                f"Robot: {observation['robot_id']} | "
                f"Valid readings: {observation['valid_measurements']} | "
                f"Nearest distance: "
                f"{observation['nearest_distance']:.2f} m | "
                f"Time: {observation['timestamp']}"
            )

    print("=" * 50)


if __name__ == "__main__":
    display_summary()