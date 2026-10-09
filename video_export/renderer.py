"""Render axis-aligned slices with optional geometry using VTK."""
from pathlib import Path

import numpy as np
import pyvista as pv


def frame_indices(count, requested):
    if requested is None or requested >= count:
        return np.arange(count)
    return np.unique(np.linspace(0, count - 1, requested).round().astype(int))


def slice_grid(dataset, axis, index, missing_value):
    x, y, z = dataset.axes
    if axis == 2:
        xx, yy = np.meshgrid(x, y, indexing="ij")
        zz = np.full(xx.shape, z[index])
    elif axis == 0:
        yy, zz = np.meshgrid(y, z, indexing="ij")
        xx = np.full(yy.shape, x[index])
    else:
        xx, zz = np.meshgrid(x, z, indexing="ij")
        yy = np.full(xx.shape, y[index])
    values = np.take(dataset.values, index, axis=axis).astype(float, copy=True)
    # Missing measurements form a continuous band at the color-scale floor.
    # Only the explicit inside mask cuts transparent holes in the slice.
    values[~np.isfinite(values)] = missing_value
    if dataset.inside is not None:
        values[np.take(dataset.inside, index, axis=axis)] = np.nan
    grid = pv.StructuredGrid(xx, yy, zz)
    grid["values"] = values.ravel(order="F")
    return grid


def color_limits(dataset, config):
    valid = np.isfinite(dataset.values)
    if dataset.inside is not None:
        valid &= ~dataset.inside
    vmax = float(dataset.values[valid].max()) if config["vmax"] is None else config["vmax"]
    vmin = vmax - config["dyn_range"] if config["vmin"] is None else config["vmin"]
    if vmin >= vmax:
        raise ValueError("vmin must be smaller than the effective vmax")
    return vmin, vmax


def make_plotter(dataset, config, limits, top_down=False):
    plotter = pv.Plotter(off_screen=True, window_size=(config["width"], config["height"]))
    try:
        plotter.set_background("white")
        plotter.enable_depth_peeling(10)
        x, y, z = dataset.axes
        center = np.array([(x[0] + x[-1]) / 2, (y[0] + y[-1]) / 2, (z[0] + z[-1]) / 2])
        if not top_down:
            plotter.add_mesh(pv.Plane(center=(center[0], center[1], config["ground_z"]),
                                     direction=(0, 0, 1), i_size=float(np.ptp(x)) * 1.06,
                                     j_size=float(np.ptp(y)) * 1.06),
                             color=(0.80, 0.78, 0.73), lighting=False)
        if dataset.faces.size:
            plotter.add_mesh(pv.PolyData(dataset.vertices, dataset.faces), color=(0.62, 0.64, 0.68),
                             opacity=config["scene_opacity"], show_edges=False)
        if dataset.marker is not None:
            plotter.add_mesh(pv.Sphere(radius=config["marker_radius"], center=dataset.marker), color="red")
        plotter.set_scale(zscale=config["z_scale"])
        center[2] *= config["z_scale"]
        radius = max(1.6 * float(np.hypot(np.ptp(x), np.ptp(y))), float(np.ptp(z)) * config["z_scale"] * 2)
        if top_down:
            plotter.camera_position = [(center + [0, 0, radius]).tolist(), center.tolist(), (0, 1, 0)]
            plotter.enable_parallel_projection()
        else:
            elevation, azimuth = np.radians([config["elevation"], config["azimuth"]])
            position = center + radius * np.array([np.cos(elevation) * np.cos(azimuth),
                                                   np.cos(elevation) * np.sin(azimuth), np.sin(elevation)])
            plotter.camera_position = [position.tolist(), center.tolist(), (0, 0, 1)]
        # Keep camera framing stable while a slice moves through the volume.
        plotter.add_mesh(pv.Box(bounds=(float(x[0]), float(x[-1]), float(y[0]), float(y[-1]),
                                        float(z[0]), float(z[-1]))), opacity=0.0, show_scalar_bar=False)
        source = pv.Line((float(x[0]), float(y[0]), float(z[0])),
                         (float(x[0]), float(y[0]), float(z[0]) + 1e-6))
        source["values"] = np.array(limits)
        small = config["width"] < 1000
        plotter.add_mesh(source, scalars="values", opacity=0.0, cmap=config["cmap"], clim=limits,
                         scalar_bar_args={"title": config["scalar_label"], "n_labels": 5, "vertical": False,
                                          "position_x": 0.54, "position_y": 0.87, "width": 0.42,
                                          "height": 0.08, "color": "black",
                                          "title_font_size": 11 if small else 18,
                                          "label_font_size": 9 if small else 14})
        return plotter
    except Exception:
        plotter.close()
        raise


def set_slice(plotter, dataset, config, limits, axis, index, coverage=False):
    plotter.add_mesh(slice_grid(dataset, axis, index, limits[0]), scalars="values", cmap=config["cmap"],
                     clim=limits, opacity=config["slice_opacity"], nan_opacity=0.0,
                     lighting=False, show_scalar_bar=False, name="data-slice", reset_camera=False)
    tag = "xyz"[axis]
    coordinate = dataset.axes[axis][index]
    title = "Coverage" if coverage else f"{tag.upper()} sweep"
    plotter.add_text(f"{title}   {tag} = {coordinate:g} {config['coordinate_unit']}",
                     position="upper_left", font_size=10 if config["width"] < 1000 else 14,
                     color="black", name="slice-label")


def coverage_index(dataset, config):
    z = dataset.axes[2]
    requested = config["coverage_z"]
    if requested is None:
        return 0
    if requested < z[0] or requested > z[-1]:
        raise ValueError(f"coverage_z must lie within [{z[0]:g}, {z[-1]:g}]")
    return int(np.argmin(np.abs(z - requested)))


def render_outputs(dataset, config, output, coverage_only=False):
    output = Path(output)
    limits = color_limits(dataset, config)
    index = coverage_index(dataset, config)
    results = []
    if not coverage_only:
        for tag in config["axes"]:
            axis = "xyz".index(tag)
            indices = frame_indices(dataset.values.shape[axis], config[f"frames_{tag}"])
            plotter = make_plotter(dataset, config, limits)
            try:
                set_slice(plotter, dataset, config, limits, axis, int(indices[0]))
                plotter.reset_camera()
                plotter.camera.zoom(config["zoom"] * 0.85)
                name = f"sweep_{tag}.mp4"
                plotter.open_movie(str(output / name), framerate=config[f"fps_{tag}"], quality=8)
                for index_value in indices:
                    set_slice(plotter, dataset, config, limits, axis, int(index_value))
                    plotter.write_frame()
                results.append(name)
                print(f"[render] {name}: {len(indices)} frames at {config[f'fps_{tag}']} fps")
            finally:
                plotter.close()
    plotter = make_plotter(dataset, config, limits, top_down=True)
    try:
        set_slice(plotter, dataset, config, limits, 2, index, coverage=True)
        plotter.reset_camera()
        plotter.camera.zoom(config["zoom"] * 0.85)
        plotter.screenshot(str(output / "coverage.png"))
        results.append("coverage.png")
        print(f"[render] coverage.png: z = {dataset.axes[2][index]:g} {config['coordinate_unit']}")
    finally:
        plotter.close()
    return results
