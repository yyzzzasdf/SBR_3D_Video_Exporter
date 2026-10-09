"""VTK slice sweeps adapted from My_SBR tools/plotting_3d/sweep_volume.py."""
from pathlib import Path
import math
import numpy as np
import pyvista as pv


def frame_indices(count, requested):
    if requested is None or requested >= count:
        return np.arange(count)
    return np.unique(np.linspace(0, count - 1, requested).round().astype(int))


def display_info(metadata, config):
    kind = metadata["value_kind"]
    if config["display"] == "path_gain" and kind == "received_power_dbw":
        power = metadata.get("tx_power_w")
        if type(power) not in (int, float) or not math.isfinite(power) or power <= 0:
            raise ValueError("path_gain display requires a positive tx_power_w in metadata.json")
        return -10.0 * math.log10(power), "Path Gain (dB)"
    return 0.0, "Path Gain (dB)" if kind == "path_gain_db" else "Received Power (dBW)"


def slice_grid(axes, cube, inside, axis, index, vmin, offset=0.0):
    x, y, z = axes
    if axis == 2:
        xx, yy = np.meshgrid(x, y, indexing="ij")
        zz = np.full(xx.shape, z[index])
        values = cube[:, :, index]
        mask = None if inside is None else inside[:, :, index]
    elif axis == 0:
        yy, zz = np.meshgrid(y, z, indexing="ij")
        xx = np.full(yy.shape, x[index])
        values = cube[index, :, :]
        mask = None if inside is None else inside[index, :, :]
    else:
        xx, zz = np.meshgrid(x, z, indexing="ij")
        yy = np.full(xx.shape, y[index])
        values = cube[:, index, :]
        mask = None if inside is None else inside[:, index, :]
    grid = pv.StructuredGrid(xx, yy, zz)
    values = np.where(np.isfinite(values), values + offset, vmin)
    if mask is not None:
        values = np.where(mask, np.nan, values)
    grid["power"] = values.ravel(order="F")
    return grid


def make_plotter(dataset, config, vmin, vmax, label):
    p = pv.Plotter(off_screen=True, window_size=(config["width"], config["height"]))
    try:
        p.set_background("white")
        p.enable_depth_peeling(10)
        x, y, z = dataset.axes
        center = np.array([(x[0] + x[-1]) / 2, (y[0] + y[-1]) / 2,
                           (z[0] + z[-1]) / 2])
        ground = pv.Plane(center=(center[0], center[1], config["ground_z"]),
                          direction=(0, 0, 1), i_size=float(np.ptp(x)) * 1.06,
                          j_size=float(np.ptp(y)) * 1.06)
        p.add_mesh(ground, color=(0.80, 0.78, 0.73), lighting=False)
        if dataset.faces.size:
            p.add_mesh(pv.PolyData(dataset.vertices, dataset.faces), color=(0.62, 0.64, 0.68),
                       opacity=config["building_opacity"], show_edges=False)
        if dataset.tx is not None:
            p.add_mesh(pv.Sphere(radius=config["tx_radius"], center=dataset.tx), color="red")
        p.set_scale(zscale=config["z_scale"])
        center[2] *= config["z_scale"]
        radius = 1.6 * float(np.hypot(np.ptp(x), np.ptp(y)))
        el, az = np.radians([config["elevation"], config["azimuth"]])
        position = center + radius * np.array([np.cos(el) * np.cos(az),
                                               np.cos(el) * np.sin(az), np.sin(el)])
        p.camera_position = [position.tolist(), center.tolist(), (0, 0, 1)]
        source = pv.Line((float(x[0]), float(y[0]), float(z[0])),
                         (float(x[0]), float(y[0]), float(z[0]) + 1e-6))
        source["power"] = np.array([vmin, vmax])
        small = config["width"] < 1000
        p.add_mesh(source, scalars="power", opacity=0.0, cmap=config["cmap"], clim=(vmin, vmax),
                   scalar_bar_args={"title": label, "n_labels": 5, "vertical": False,
                                    "position_x": 0.54, "position_y": 0.86, "width": 0.43,
                                    "height": 0.09, "color": "black",
                                    "title_font_size": 11 if small else 20,
                                    "label_font_size": 9 if small else 16})
        return p
    except Exception:
        p.close()
        raise


def render_outputs(dataset, config, output, preview_only=False):
    output = Path(output)
    offset, label = display_info(dataset.metadata, config)
    results = []
    for quantity, cube in dataset.powers.items():
        vmax = config["vmax"]
        vmax = float(np.nanmax(cube)) + offset if vmax is None else vmax
        vmin = vmax - config["dyn_range"] if config["vmin"] is None else config["vmin"]
        if vmin >= vmax:
            raise ValueError(f"{quantity}: vmin must be smaller than the effective vmax")
        for tag in config["axes"]:
            axis = "xyz".index(tag)
            indices = frame_indices(cube.shape[axis], config[f"frames_{tag}"])
            coordinates = dataset.axes[axis]
            p = make_plotter(dataset, config, vmin, vmax, label)
            try:
                def set_slice(index):
                    grid = slice_grid(dataset.axes, cube, dataset.inside, axis, index, vmin, offset)
                    p.add_mesh(grid, scalars="power", cmap=config["cmap"], clim=(vmin, vmax),
                               opacity=config["slice_opacity"], nan_opacity=0.0,
                               show_scalar_bar=False, name="power-slice", reset_camera=False)
                    p.add_text(f"{tag}-sweep   {tag} = {coordinates[index]:.1f} m   {quantity}",
                               font_size=10 if config["width"] < 1000 else 14,
                               color="black", name="sweep-label")
                set_slice(int(indices[0]))
                p.reset_camera()
                p.camera.zoom(config["zoom"])
                if config["preview"] or preview_only:
                    idx = int(np.argmin(np.abs(coordinates - dataset.tx[axis]))) if dataset.tx is not None and axis != 2 else len(coordinates) // 2
                    set_slice(idx)
                    preview = output / f"preview3d_{tag}_{quantity}.png"
                    p.screenshot(str(preview))
                    results.append({"file": preview.name, "kind": "preview", "slice_index": idx})
                if not preview_only:
                    video = output / f"sweep3d_{tag}_{quantity}.mp4"
                    p.open_movie(str(video), framerate=config[f"fps_{tag}"], quality=8)
                    for index in indices:
                        set_slice(int(index))
                        p.write_frame()
                    results.append({"file": video.name, "kind": "video", "frames": len(indices),
                                    "fps": config[f"fps_{tag}"], "slice_indices": indices.tolist(),
                                    "vmin": vmin, "vmax": vmax, "label": label})
                print(f"[render] {quantity}/{tag}: {len(indices)} slices")
            finally:
                p.close()
    return results
