#!/usr/bin/env python
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of ANTS and is released under the BSD 3-Clause license.
# See LICENSE.txt in the root of the repository for full licensing details.
from pathlib import Path

import cartopy.crs as ccrs
import iris.plot as iplt
import matplotlib.pyplot as plt


def plot_title_generator(kgo_cube, test_output_cube):
    """
    Generate title for the plot using the standard_name of both datasets.

    Parameters
    ----------
    kgo_cube : iris.cube.Cube
        The kgo cube related to the nccmp task that has failed.

    actual_result_filepath : iris.cube.Cube
        The test result cube related to the nccmp task that has failed.

    Returns
    -------
    str : The title for the plot.

    """
    kgo_title = kgo_cube.standard_name
    test_output_cube_title = test_output_cube.standard_name
    if kgo_title == test_output_cube_title:
        return f"standard_name of both datasets:{test_output_cube.standard_name}"

    else:
        return f"KG0 standard_name: {kgo_title}, \
            Test output data standard_name: {test_output_cube_title}"


def generate_kgo_plot(ax, kgo_slice_of_interest):
    """
    Generate KGO plot.

    Parameters
    ----------
    ax : cartopy.mpl.geoaxes.GeoAxes
        The map projection used for the plot.
    kgo_slice_of_interest : iris.cube.Cube
        The slice in the kgo cube where the slice of greatest difference
        was located.
    """
    plt.sca(ax)
    iplt.pcolormesh(kgo_slice_of_interest)
    colourbar = plt.colorbar(pad=0.01, location="bottom")
    colourbar.ax.tick_params(labelsize=40)
    ax.coastlines()
    ax.set_title("KGO", fontsize=80)


def generate_test_output_plot(ax, test_result_slice_of_interest):
    """
    Generate Test Output plot.

    Parameters
    ----------
    ax : cartopy.mpl.geoaxes.GeoAxes
        The map projection used for the plot.
    test_result_slice_of_interest : iris.cube.Cube
        The slice in the test data where the slice of greatest difference
        was located.
    """
    plt.sca(ax)
    iplt.pcolormesh(test_result_slice_of_interest)
    colourbar = plt.colorbar(pad=0.01, location="bottom")
    colourbar.ax.tick_params(labelsize=40)
    ax.coastlines()
    ax.set_title("Test output", fontsize=80)


def generate_absolute_difference_plot(ax, slice_of_greatest_difference):
    """
    Generate Absolute Difference plot.

    Parameters
    ----------
    ax : cartopy.mpl.geoaxes.GeoAxes
        The map projection used for the plot.
    slice_of_greatest_difference : iris.cube.Cube
        The slice with greatest absolute difference between the KGO and
        test data.
    """
    plt.sca(ax)
    iplt.pcolormesh(slice_of_greatest_difference)
    colourbar = plt.colorbar(pad=0.01, location="bottom")
    colourbar.ax.tick_params(labelsize=40)
    ax.coastlines()
    ax.set_title("Absolute Difference", fontsize=80)


def generate_log_difference_plot(ax, log_difference_cube):
    """
    Generate Log Difference plot.

    Parameters
    ----------
    ax : cartopy.mpl.geoaxes.GeoAxes
        The map projection used for the plot.
    log_difference_cube : iris.cube.Cube
        The log difference cube generated from the log-transformed data of the
        KGO slice and the test result slice.
    """
    plt.sca(ax)
    iplt.pcolormesh(log_difference_cube)
    colourbar = plt.colorbar(pad=0.01, location="bottom")
    colourbar.ax.tick_params(labelsize=40)
    ax.coastlines()
    ax.set_title("Log difference", fontsize=80)


def generate_relative_error_plot(ax, relative_error_cube):
    """
    Generate Relative Error plot.

    Parameters
    ----------
    ax : cartopy.mpl.geoaxes.GeoAxes
        The map projection used for the plot.
    relative_error_cube : iris.cube.Cube
        A relative error cube from the two slices where greatest difference
        have been detected.
    """
    plt.sca(ax)
    iplt.pcolormesh(relative_error_cube)
    colourbar = plt.colorbar(pad=0.01, location="bottom")
    colourbar.ax.tick_params(labelsize=40)
    ax.coastlines()
    ax.set_title("Relative error (as percentage)", fontsize=80)


def generate_plots(
    plot_title,
    slice_of_greatest_difference,
    kgo_slice_of_interest,
    test_result_slice_of_interest,
    log_difference_cube,
    relative_error_cube,
):
    """
    Generate plots using the provided cubes.

    Parameters
    ----------
    plot_title : str
        The title for the top of the plot.

    slice_of_greatest_difference : iris.cube.Cube
        The slice with greatest absolute difference between the KGO and test
        data.

    kgo_slice_of_interest : iris.cube.Cube
        The slice in the kgo cube where the slice of greatest difference was
        located.

    test_result_slice_of_interest : iris.cube.Cube
        The slice in the test data where the slice of greatest difference was
        located.

    log_difference_cube : iris.cube.Cube
        The log difference cube generated from the log-transformed data of the
        KGO slice and the test result slice.

    relative_error_cube : iris.cube.Cube
        A relative error cube from the two slices where greatest difference
        have been detected.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The figure object containing the plot.
    ax : cartopy.mpl.geoaxes.GeoAxes
        The map projection used for the plot.
    """

    fig, axs = plt.subplots(
        nrows=3,
        ncols=2,
        figsize=(60, 50),
        subplot_kw={"projection": ccrs.PlateCarree()},
        layout="constrained",
    )
    fig.suptitle(f"{plot_title}", fontsize=80, fontweight="semibold")

    generate_kgo_plot(axs[0, 0], kgo_slice_of_interest)

    generate_test_output_plot(axs[0, 1], test_result_slice_of_interest)

    generate_absolute_difference_plot(axs[1, 0], slice_of_greatest_difference)

    generate_log_difference_plot(axs[1, 1], log_difference_cube)

    generate_relative_error_plot(axs[2, 0], relative_error_cube)

    return fig, axs


def save_plot(kgo_filepath, plot_output_filepath):
    """
    Save the generated plots to the output file path.

    Parameters
    ----------
    kgo_filepath : str
        The file path of the input data used to generate the plot.
    plot_output_filepath : str
        The directory path where the plots will be saved.

    Returns
    -------
    None
        This function does not return any value.
    """
    filename = Path(kgo_filepath).stem
    plt.savefig(f"{plot_output_filepath}/{filename}.png", bbox_inches="tight")
    print(
        f"[INFO] Comparison plots successfully saved here: "
        f"{plot_output_filepath}/{filename}.png"
    )
