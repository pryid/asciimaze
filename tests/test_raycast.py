import math

import pytest

from maze3d.raycast import cast_ray, compute_wall_span, floorcast_sample_row
from maze3d.style import Style


def dummy_style(*, unicode_ok: bool = False) -> Style:
    # Keep colors disabled so tests don't require curses initialization.
    return Style(
        unicode_ok=unicode_ok,
        colors_ok=False,
        color_mode="none",
        wall_pairs=[],
        floor_pairs=[],
        hud_pair=0,
        map_wall_pair=0,
        map_floor_pair=0,
        map_player_pair=0,
        map_goal_pair=0,
    )


def test_cast_ray_hits_expected_wall_distance() -> None:
    grid = [
        "###",
        "# #",
        "###",
    ]
    dist, side = cast_ray(grid, 1.5, 1.5, 0.0)  # facing east
    assert dist == pytest.approx(0.5, abs=1e-6)
    assert side in (0, 1)


def test_compute_wall_span_orders_top_and_bottom() -> None:
    top, bot = compute_wall_span(height=40, dist=2.0, cam_z=0.0, mid=20.0)
    assert top <= bot


def test_floorcast_sample_row_flat_mode_wraps_inside_grid() -> None:
    grid = [
        "###",
        "# #",
        "###",
    ]
    px, py = 1.5, 1.5
    cos_arr = [1.0, 0.0]
    sin_arr = [0.0, 0.0]

    hit_top, floor_ch, floor_attr, top_ch, top_attr = floorcast_sample_row(
        grid,
        px,
        py,
        cos_arr,
        sin_arr,
        dist_plane=2.0,
        dist_plane_top=0.5,
        style=dummy_style(unicode_ok=False),
        shadows_on=False,
    )

    assert floor_ch == "."
    assert top_ch == "#"
    assert len(hit_top) == 2
    assert hit_top[0] is True  # points into the east wall
    assert hit_top[1] is False  # points at current open cell

    # Attrs should be integers (curses attributes).
    assert isinstance(floor_attr, int)
    assert isinstance(top_attr, int)
