import random

from maze3d.constants import FREE_MAX_Z, OPEN, WALL, WALL_HEIGHT
from maze3d.maze import find_path_cells, generate_maze, resolve_floor_collision
from maze3d.models import Player


def test_generate_maze_dimensions_and_borders() -> None:
    rng = random.Random(0)
    cell_w, cell_h = 4, 3
    grid = generate_maze(cell_w, cell_h, rng)

    assert len(grid) == cell_h * 2 + 1
    assert all(len(row) == cell_w * 2 + 1 for row in grid)

    # Outer border should be walls.
    assert set(grid[0]) == {WALL}
    assert set(grid[-1]) == {WALL}
    for row in grid:
        assert row[0] == WALL
        assert row[-1] == WALL

    # There should be at least one open cell.
    assert any(OPEN in row for row in grid)


def test_find_path_cells_returns_adjacent_open_steps() -> None:
    grid = [
        "#####",
        "#   #",
        "# # #",
        "#   #",
        "#####",
    ]
    start = (1, 1)
    goal = (3, 3)

    path = find_path_cells(grid, start, goal)

    assert path[0] == start
    assert path[-1] == goal

    for x, y in path:
        assert grid[y][x] == OPEN

    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        assert dx + dy == 1


def test_resolve_floor_collision_clamps_to_floor_and_ceiling() -> None:
    grid = [
        "###",
        "# #",
        "###",
    ]

    # If player is in a wall cell (rare in real play), floor height should clamp them up.
    p1 = Player(x=0.5, y=0.5, z=0.0, ang=0.0, vz=-1.0)
    resolve_floor_collision(grid, p1)
    assert p1.z == WALL_HEIGHT
    assert p1.vz == 0.0

    # Free-fly mode clamps maximum Z.
    p2 = Player(x=1.5, y=1.5, z=FREE_MAX_Z + 10.0, ang=0.0, vz=1.0)
    resolve_floor_collision(grid, p2)
    assert p2.z == FREE_MAX_Z
    assert p2.vz == 0.0
