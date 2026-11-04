"""OD-01: losowa pozycja startowa Plant nie leży we wnętrzu brył kolizyjnych."""

from pathlib import Path

import pytest

from linumert.machine.schema import load_machine
from linumert_plant.build_machine import collision_free_start
from linumert_plant.collisions import CollisionModel

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("seed", range(1, 40))
def test_random_start_has_no_collision(seed):  # REQ-QA-02
    cfg = load_machine(ROOT / "config/machines/router_atc_rack.yaml")
    pose = collision_free_start(cfg, seed)
    if pose is None:  # losowanie rdzenia C jest wolne od kolizji
        return
    nose = [pose[letter] for letter in "XYZ"]
    assert not CollisionModel.from_config(cfg).check(0.0, nose)


def test_seed_1_collides_and_is_replaced():  # REQ-QA-02
    cfg = load_machine(ROOT / "config/machines/router_atc_rack.yaml")
    assert collision_free_start(cfg, 1) is not None


def test_start_is_deterministic_per_seed():  # REQ-QA-02
    cfg = load_machine(ROOT / "config/machines/router_atc_rack.yaml")
    assert collision_free_start(cfg, 7) == collision_free_start(cfg, 7)
