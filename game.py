import argparse
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


Coordinate = Tuple[int, int]


@dataclass
class BanguCar:
    position: Coordinate
    grid_size: Coordinate
    hp: int = 3
    base_speed: int = 3
    base_range: int = 1
    speed_bonus_turns: int = 0
    range_bonus_turns: int = 0
    items: Dict[str, int] = field(default_factory=lambda: {"speed": 1, "range": 1})

    @property
    def speed(self) -> int:
        return self.base_speed + (1 if self.speed_bonus_turns > 0 else 0)

    @property
    def gas_range(self) -> int:
        return self.base_range + (1 if self.range_bonus_turns > 0 else 0)

    def tick_effects(self) -> None:
        if self.speed_bonus_turns > 0:
            self.speed_bonus_turns -= 1
        if self.range_bonus_turns > 0:
            self.range_bonus_turns -= 1

    def use_item(self, name: str) -> bool:
        if self.items.get(name, 0) <= 0:
            return False
        if name == "speed":
            self.speed_bonus_turns = 3
        elif name == "range":
            self.range_bonus_turns = 5
        else:
            return False
        self.items[name] -= 1
        return True

    def move(self, direction: str, steps: int) -> None:
        dx, dy = 0, 0
        if direction == "up":
            dy = -steps
        elif direction == "down":
            dy = steps
        elif direction == "left":
            dx = -steps
        elif direction == "right":
            dx = steps
        else:
            raise ValueError("unknown direction")
        max_x, max_y = self.grid_size
        new_x = max(0, min(max_x - 1, self.position[0] + dx))
        new_y = max(0, min(max_y - 1, self.position[1] + dy))
        self.position = (new_x, new_y)


@dataclass
class Monster:
    position: Coordinate
    speed: int

    def step_toward(self, target: Coordinate, grid_size: Coordinate) -> None:
        tx, ty = target
        mx, my = self.position
        for _ in range(self.speed):
            if mx < tx:
                mx += 1
            elif mx > tx:
                mx -= 1
            if my < ty:
                my += 1
            elif my > ty:
                my -= 1
        max_x, max_y = grid_size
        self.position = (
            max(0, min(max_x - 1, mx)),
            max(0, min(max_y - 1, my)),
        )


@dataclass
class Stage:
    level: int
    grid_size: Coordinate
    monsters: List[Monster]
    flag: Coordinate

    @classmethod
    def create(cls, level: int) -> "Stage":
        width = min(18, 10 + level)
        height = min(18, 10 + level)
        grid_size = (width, height)
        monster_count = 3 + level * 2
        monster_speed = 1 + (level - 1) // 3
        monsters: List[Monster] = []
        occupied = {(0, 0)}
        while len(monsters) < monster_count:
            pos = (random.randint(0, width - 1), random.randint(0, height - 1))
            if pos in occupied:
                continue
            occupied.add(pos)
            monsters.append(Monster(position=pos, speed=monster_speed))
        flag = (width - 1, height - 1)
        return cls(level=level, grid_size=grid_size, monsters=monsters, flag=flag)


class Game:
    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            random.seed(seed)
        self.stage_level = 1
        self.car = BanguCar(position=(0, 0), grid_size=(10, 10))

    def start(self) -> None:
        print("Welcome to the 방구차 flag race! Reach the flag before your HP hits zero.")
        while True:
            stage = Stage.create(self.stage_level)
            self.car.position = (0, 0)
            self.car.grid_size = stage.grid_size
            print(f"\n--- Stage {stage.level} ---")
            print(f"Grid: {stage.grid_size[0]}x{stage.grid_size[1]}. Monsters: {len(stage.monsters)}. Difficulty: {stage.monsters[0].speed if stage.monsters else 1}.")
            if not self.run_stage(stage):
                break
            self.stage_level += 1
        print("Game over! Thanks for playing.")

    def run_stage(self, stage: Stage) -> bool:
        while True:
            self.render(stage)
            command = input("Command (move/use/status/help/quit): ").strip().lower()
            if command == "quit":
                return False
            if command == "help":
                self.print_help()
                continue
            if command == "status":
                self.print_status()
                continue
            if command.startswith("use"):
                _, _, item = command.partition(" ")
                if self.car.use_item(item):
                    print(f"Used {item}! Bonuses are active for a few turns.")
                else:
                    print("Item not available.")
                self.after_player_action(stage)
                continue
            if command.startswith("move"):
                parts = command.split()
                if len(parts) != 3:
                    print("Move format: move <up/down/left/right> <steps>")
                    continue
                _, direction, steps_text = parts
                try:
                    steps = int(steps_text)
                except ValueError:
                    print("Steps must be a number.")
                    continue
                if steps < 0 or steps > self.car.speed:
                    print(f"You can move 0-{self.car.speed} tiles this turn.")
                    continue
                try:
                    self.car.move(direction, steps)
                except ValueError:
                    print("Unknown direction. Use up, down, left, or right.")
                    continue
                self.after_player_action(stage)
                if self.car.position == stage.flag:
                    print(f"Stage {stage.level} clear! You secured the flag.")
                    return True
                continue
            print("Unknown command. Type 'help' for options.")

    def after_player_action(self, stage: Stage) -> None:
        self.resolve_gas(stage)
        if self.car.hp <= 0:
            return
        for monster in stage.monsters[:]:
            monster.step_toward(self.car.position, stage.grid_size)
            if monster.position == self.car.position:
                stage.monsters.remove(monster)
                self.car.hp -= 1
                print("A monster collided with you and perished! HP -1.")
        self.resolve_gas(stage)
        self.car.tick_effects()
        if self.car.hp <= 0:
            print("Your 방구차 ran out of steam.")

    def resolve_gas(self, stage: Stage) -> None:
        killed = 0
        car_x, car_y = self.car.position
        for monster in stage.monsters[:]:
            mx, my = monster.position
            if abs(mx - car_x) + abs(my - car_y) <= self.car.gas_range:
                stage.monsters.remove(monster)
                killed += 1
        if killed:
            print(f"Your gas cloud eliminated {killed} monster(s)!")

    def render(self, stage: Stage) -> None:
        max_x, max_y = stage.grid_size
        grid = [["."] * max_x for _ in range(max_y)]
        fx, fy = stage.flag
        grid[fy][fx] = "F"
        for monster in stage.monsters:
            mx, my = monster.position
            grid[my][mx] = "M"
        cx, cy = self.car.position
        grid[cy][cx] = "B"
        print("\n" + "\n".join(" ".join(row) for row in grid))
        print(f"HP: {self.car.hp} | Speed: {self.car.speed} | Gas range: {self.car.gas_range} | Items: {self.car.items}")

    def print_help(self) -> None:
        print(
            "Commands:\n"
            "  move <direction> <steps> : Move up to your speed.\n"
            "  use <speed|range>        : Activate an item bonus.\n"
            "  status                   : Show current stats.\n"
            "  help                     : Show this help.\n"
            "  quit                     : Exit the game."
        )

    def print_status(self) -> None:
        print(
            f"Stage {self.stage_level} | HP {self.car.hp} | Speed {self.car.speed} (base {self.car.base_speed}) | "
            f"Gas range {self.car.gas_range} (base {self.car.base_range}) | Items {self.car.items}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Turn-based 방구차 flag game")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible stages")
    args = parser.parse_args()
    game = Game(seed=args.seed)
    game.start()


if __name__ == "__main__":
    main()
