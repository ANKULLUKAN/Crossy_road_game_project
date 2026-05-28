import json

from lane import Lane
from lane_types import LaneType
from obstacle import Obstacle


def save_game(game, filename="save.json"):
    data = {
        "player_col": game.player_col,
        "player_world_row": game.player_world_row,
        "player_screen_row": game.player_screen_row,
        "player_x": getattr(game, "player_x", game.player_col * 50 + 5),
        "difficulty": game.difficulty,
        "is_alive": game.is_alive,
        "start_word_row": game.start_word_row,
        "last_difficulty_step": game.last_difficulty_step,
        "preset_label": getattr(game, "preset", {}).get("label", "Normalny"),
        "preset_name": getattr(game, "preset", {}).get("name", "Klasyczny"),
        "camera_speed": getattr(game, "camera_speed", 0.3),
        "show_grid": getattr(game, "show_grid", False),
        "lanes": []
    }

    for row, lane in game.lanes.items():
        lane_data = {
            "row": row,
            "index": lane.index,
            "lane_type": lane.lane_type.name,
            "direction": lane.direction,
            "speed": lane.speed,
            "spawn_interval": lane.spawn_interval,
            "spawn_timer": lane.spawn_timer,
            "obstacles": []
        }

        for obs in lane.obstacles:
            obs_data = {
                "x": obs.x,
                "y": obs.y,
                "width": obs.width,
                "height": obs.height,
                "speed": obs.speed,
                "direction": obs.direction,
                "color": obs.color,
                "obstacle_type": obs.obstacle_type,
                "solid": obs.solid,
                "deadly": obs.deadly
            }
            lane_data["obstacles"].append(obs_data)

        data["lanes"].append(lane_data)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    if hasattr(game, "logger"):
        game.logger.log("SAVE_GAME", f"saved to {filename}")


def load_game(game, filename="save.json"):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    game.player_col = data["player_col"]
    game.player_world_row = data["player_world_row"]
    game.player_screen_row = data["player_screen_row"]
    game.player_x = data["player_x"]
    game.difficulty = data["difficulty"]
    game.is_alive = data["is_alive"]
    game.start_word_row = data["start_word_row"]
    game.last_difficulty_step = data["last_difficulty_step"]
    if hasattr(game, "preset"):
        game.preset = dict(game.preset)
        game.preset["label"] = data.get("preset_label", game.preset.get("label", "Normalny"))
        game.preset["name"] = data.get("preset_name", game.preset.get("name", "Klasyczny"))
    game.camera_speed = data.get("camera_speed", getattr(game, "camera_speed", 0.3))
    game.show_grid = data.get("show_grid", getattr(game, "show_grid", False))

    game.lanes = {}

    for lane_data in data["lanes"]:
        lane = Lane(
            index=lane_data["index"],
            lane_type=LaneType[lane_data["lane_type"]],
            direction=lane_data["direction"],
            speed=lane_data["speed"],
            spawn_interval=lane_data["spawn_interval"]
        )

        lane.spawn_timer = lane_data["spawn_timer"]

        for obs_data in lane_data["obstacles"]:
            obs = Obstacle(
                x=obs_data["x"],
                y=obs_data["y"],
                width=obs_data["width"],
                height=obs_data["height"],
                speed=obs_data["speed"],
                direction=obs_data["direction"],
                color=obs_data["color"],
                obstacle_type=obs_data["obstacle_type"],
                solid=obs_data["solid"],
                deadly=obs_data["deadly"]
            )
            lane.obstacles.append(obs)

        game.lanes[lane_data["row"]] = lane

    if hasattr(game, "logger"):
        game.logger.log("LOAD_GAME", f"loaded from {filename}")