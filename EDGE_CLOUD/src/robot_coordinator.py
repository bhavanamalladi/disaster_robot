"""
Edge Cloud - Robot Coordinator

Features:
1. Robot heartbeat monitoring
2. Offline detection
3. Robot recovery
4. Task assignment
5. Distance-based robot selection
6. Error handling and recovery
"""

import sys
import os
import math
import sqlite3

from datetime import datetime, timezone

# Add Edge Cloud source directory to Python path
sys.path.insert(
    0,
    os.path.dirname(os.path.abspath(__file__))
)

import database


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROBOTS = [
    "reference_ugv",
    "robot_2"
]

HEARTBEAT_TIMEOUT = 10


# --------------------------------------------------
# ROBOT HEARTBEAT MANAGEMENT
# --------------------------------------------------

def send_heartbeat(robot_id):
    """Update robot communication time and recover if offline."""

    if robot_id not in ROBOTS:
        print(f"ERROR: Unknown robot: {robot_id}")
        return False

    try:
        robot_statuses = database.get_all_robot_status()

        current_status = next(
            (
                robot for robot in robot_statuses
                if robot["robot_id"] == robot_id
            ),
            None
        )

        if current_status is None:

            database.update_robot_status(
                robot_id,
                "AVAILABLE"
            )

        else:

            task_id = current_status["current_task_id"]
            new_status = current_status["status"]

            # Recover an offline robot
            if new_status == "OFFLINE":

                tasks = database.get_all_search_tasks()

                active_task = next(
                    (
                        task for task in tasks
                        if task["task_id"] == task_id
                        and task["status"] == "IN_PROGRESS"
                    ),
                    None
                )

                if active_task:
                    new_status = "BUSY"
                else:
                    new_status = "AVAILABLE"
                    task_id = None

            database.update_robot_status(
                robot_id,
                new_status,
                task_id
            )

        print(f"Heartbeat received from {robot_id}")
        return True

    except (sqlite3.Error, ValueError) as error:
        print(f"Heartbeat error for {robot_id}: {error}")
        return False


# --------------------------------------------------
# ROBOT COMMUNICATION MONITORING
# --------------------------------------------------

def check_robot_communication():
    """Check communication status of every registered robot."""

    try:
        current_time = datetime.now(timezone.utc)

        robot_statuses = database.get_all_robot_status()

        for robot in robot_statuses:

            try:
                last_seen = datetime.fromisoformat(
                    robot["last_seen"]
                )

                # Handle timestamps without timezone information
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(
                        tzinfo=timezone.utc
                    )

                time_difference = (
                    current_time - last_seen
                ).total_seconds()

                if time_difference > HEARTBEAT_TIMEOUT:

                    if robot["status"] != "OFFLINE":

                        print(
                            f"WARNING: {robot['robot_id']} "
                            "has stopped communicating!"
                        )

                        database.update_robot_status(
                            robot["robot_id"],
                            "OFFLINE",
                            robot["current_task_id"]
                        )

                else:

                    print(
                        f"{robot['robot_id']} is ONLINE "
                        f"({time_difference:.2f}s since heartbeat)"
                    )

            except (ValueError, TypeError) as error:

                print(
                    f"Invalid heartbeat timestamp for "
                    f"{robot['robot_id']}: {error}"
                )

    except sqlite3.Error as error:
        print(f"Communication monitoring database error: {error}")


# --------------------------------------------------
# TASK ASSIGNMENT
# --------------------------------------------------

def assign_task(robot_id, task_id):
    """Assign a pending task to an available robot atomically."""

    if robot_id not in ROBOTS:
        print(f"ERROR: Unknown robot: {robot_id}")
        return False

    try:
        robot_statuses = database.get_all_robot_status()

        robot = next(
            (
                r for r in robot_statuses
                if r["robot_id"] == robot_id
            ),
            None
        )

        if robot is None:
            print(f"Robot {robot_id} is not registered.")
            return False

        if robot["status"] != "AVAILABLE":
            print(f"Robot {robot_id} is not available.")
            return False

        if robot["current_task_id"] is not None:
            print(
                f"Robot {robot_id} already has task "
                f"{robot['current_task_id']} assigned."
            )
            return False

        tasks = database.get_all_search_tasks()

        task = next(
            (
                t for t in tasks
                if t["task_id"] == task_id
            ),
            None
        )

        if task is None:
            print(f"Task {task_id} does not exist.")
            return False

        if task["status"] != "PENDING":
            print(f"Task {task_id} is not pending.")
            return False

        if task["robot_id"] not in (None, robot_id):
            print(
                f"Task {task_id} is assigned to another robot."
            )
            return False

        # Update both records within one database transaction
        timestamp = database.get_timestamp()

        with sqlite3.connect(database.DATABASE_PATH) as connection:

            robot_result = connection.execute("""
                UPDATE robot_status
                SET status = 'BUSY',
                    current_task_id = ?,
                    last_seen = ?
                WHERE robot_id = ?
                  AND status = 'AVAILABLE'
                  AND current_task_id IS NULL
            """, (
                task_id,
                timestamp,
                robot_id
            ))

            if robot_result.rowcount != 1:
                print("Task assignment failed: Robot status changed.")
                return False

            task_result = connection.execute("""
                UPDATE search_tasks
                SET robot_id = ?,
                    status = 'IN_PROGRESS',
                    updated_at = ?
                WHERE task_id = ?
                  AND status = 'PENDING'
                  AND (robot_id IS NULL OR robot_id = ?)
            """, (
                robot_id,
                timestamp,
                task_id,
                robot_id
            ))

            if task_result.rowcount != 1:
                raise ValueError(
                    "Task status changed during assignment."
                )

        print(
            f"Task {task_id} assigned to "
            f"{robot_id} successfully."
        )

        return True

    except (sqlite3.Error, ValueError) as error:

        print(f"Task assignment error: {error}")
        return False


# --------------------------------------------------
# DISTANCE CALCULATION
# --------------------------------------------------

def calculate_distance(robot_x, robot_y, zone_x, zone_y):
    """Calculate Euclidean distance between robot and search zone."""

    return math.hypot(
        zone_x - robot_x,
        zone_y - robot_y
    )


# --------------------------------------------------
# NEAREST ROBOT SELECTION
# --------------------------------------------------

def select_nearest_available_robot(zone_x, zone_y):
    """Select the nearest available robot."""

    try:
        robot_statuses = database.get_all_robot_status()
        positions = database.get_latest_robot_positions()

        candidates = []

        for robot in robot_statuses:

            if robot["status"] != "AVAILABLE":
                continue

            if robot["current_task_id"] is not None:
                continue

            position = next(
                (
                    p for p in positions
                    if p["robot_id"] == robot["robot_id"]
                ),
                None
            )

            if position is None:
                continue

            distance = calculate_distance(
                float(position["x"]),
                float(position["y"]),
                float(zone_x),
                float(zone_y)
            )

            candidates.append(
                (robot["robot_id"], distance)
            )

        if not candidates:
            print("No available robots found.")
            return None

        candidates.sort(key=lambda item: item[1])

        selected_robot = candidates[0]

        print(
            f"Selected robot: {selected_robot[0]} "
            f"(Distance: {selected_robot[1]:.2f} m)"
        )

        return selected_robot[0]

    except (sqlite3.Error, ValueError, TypeError) as error:

        print(f"Robot selection error: {error}")
        return None


# --------------------------------------------------
# ROBOT SELECTION TEST
# --------------------------------------------------

def test_robot_selection():
    """Test distance-based selection using sample positions."""

    test_positions = [
        {
            "robot_id": "reference_ugv",
            "x": 0.0,
            "y": 0.0
        },
        {
            "robot_id": "robot_2",
            "x": 2.0,
            "y": 0.0
        }
    ]

    zone_x = 4.0
    zone_y = 3.0

    distances = []

    for position in test_positions:

        distance = calculate_distance(
            position["x"],
            position["y"],
            zone_x,
            zone_y
        )

        distances.append(
            (position["robot_id"], distance)
        )

    selected = min(
        distances,
        key=lambda item: item[1]
    )

    print("Selected robot:", selected[0])
    print("Distance:", round(selected[1], 2), "m")


# --------------------------------------------------
# AUTOMATIC TASK ALLOCATION
# --------------------------------------------------

def allocate_task_by_distance(task_id, zone_x, zone_y):
    """Select the nearest available robot and allocate a task."""

    try:
        tasks = database.get_all_search_tasks()

        task = next(
            (
                t for t in tasks
                if t["task_id"] == task_id
            ),
            None
        )

        if task is None:
            print(f"Task {task_id} does not exist.")
            return False

        if task["status"] != "PENDING":
            print(f"Task {task_id} is not pending.")
            return False

        robot_id = select_nearest_available_robot(
            zone_x,
            zone_y
        )

        if robot_id is None:
            print("Task allocation failed: No available robot.")
            return False

        success = assign_task(
            robot_id,
            task_id
        )

        if success:
            print(
                f"Task {task_id} allocated successfully "
                f"to {robot_id}."
            )

        return success

    except (sqlite3.Error, ValueError, TypeError) as error:

        print(f"Task allocation error: {error}")
        return False


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    print("EDGE CLOUD - ROBOT COORDINATOR")

    check_robot_communication()