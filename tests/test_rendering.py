import json
from pathlib import Path
import imageio.v2 as imageio
import numpy as np
import pytest
from video_export.cli import main
from video_export.config import load_config
from video_export.data import load_dataset
from video_export.renderer import display_info, slice_grid
from video_export.samples import generate_synthetic


def test_slice_orientation_and_unit_conversion():
    axes = (np.arange(3.), np.arange(4.), np.arange(5.))
    cube = np.arange(60., dtype=float).reshape(3, 4, 5)
    mask = np.zeros(cube.shape, dtype=bool)
    mask[1, 2, 3] = True
    offset, label = display_info({"value_kind": "received_power_dbw", "tx_power_w": 10},
                                load_config(overrides={"display": "path_gain"}))
    assert offset == pytest.approx(-10.) and label == "Path Gain (dB)"
    for axis, index in [(0, 1), (1, 2), (2, 3)]:
        grid = slice_grid(axes, cube, mask, axis, index, -200, offset)
        expected = np.take(cube, index, axis=axis) + offset
        expected = np.where(np.take(mask, index, axis=axis), np.nan, expected)
        np.testing.assert_allclose(grid["power"], expected.ravel(order="F"), equal_nan=True)


def test_path_gain_needs_transmit_power():
    with pytest.raises(ValueError, match="tx_power_w"):
        display_info({"value_kind": "received_power_dbw"}, load_config(overrides={"display": "path_gain"}))


def test_real_mp4_and_overwrite_protection(tmp_path):
    data = generate_synthetic(tmp_path / "input")
    config = tmp_path / "quick.json"
    config.write_text(json.dumps({"axes": ["y"], "quantities": ["coherent"],
                                 "width": 640, "height": 480, "frames_y": 3, "fps_y": 3}))
    output = tmp_path / "output"
    arguments = ["--data", str(data), "--config", str(config), "--out", str(output)]
    assert main(arguments) == 0
    video = output / "sweep3d_y_coherent.mp4"
    reader = imageio.get_reader(video, format="ffmpeg")
    try:
        assert reader.count_frames() == 3
        assert reader.get_data(0).shape == (480, 640, 3)
    finally:
        reader.close()
    run = json.loads((output / "run.json").read_text())
    assert run["status"] == "complete"
    assert len(run["inputs"]) == 4
    assert all(len(item["sha256"]) == 64 for item in run["inputs"])
    before = video.read_bytes()
    assert main(arguments) == 2
    assert video.read_bytes() == before


def test_validate_only_has_no_output(tmp_path):
    data = generate_synthetic(tmp_path / "input")
    config = tmp_path / "quick.json"
    config.write_text("{}")
    output = tmp_path / "never_created"
    assert main(["--data", str(data), "--config", str(config), "--out", str(output), "--validate-only"]) == 0
    assert not output.exists()
