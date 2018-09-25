from autolens import exc
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np
from astropy.io import fits

def plot_array(array, grid, as_subplot,
               xticks, yticks, xyticksize, units,
               norm, norm_min, norm_max, linthresh, linscale,
               figsize, aspect, cmap, cb_ticksize,
               title, titlesize, xlabelsize, ylabelsize,
               output_path, output_filename, output_format):
    xlabel, ylabel = get_xylabels(units)

    norm_min, norm_max = get_normalization_min_max(array=array, norm_min=norm_min, norm_max=norm_max)
    norm_scale = get_normalization_scale(norm=norm, norm_min=norm_min, norm_max=norm_max,
                                              linthresh=linthresh, linscale=linscale)

    plot_image(array=array, grid=grid, as_subplot=as_subplot, figsize=figsize, aspect=aspect, cmap=cmap,
                    norm_scale=norm_scale)
    set_ticks(array=array, units=units, xticks=xticks, yticks=yticks, xyticksize=xyticksize)
    set_title_and_labels(title=title, xlabel=xlabel, ylabel=ylabel, titlesize=titlesize,
                              xlabelsize=xlabelsize, ylabelsize=ylabelsize)
    set_colorbar(cb_ticksize=cb_ticksize)
    plot_grid(grid)

    if not as_subplot:
        output_array(array=array, output_path=output_path, output_filename=output_filename,
                          output_format=output_format)
        plt.close()

def get_normalization_min_max(array, norm_min, norm_max):
    if norm_min is None:
        norm_min = array.min()
    if norm_max is None:
        norm_max = array.max()

    return norm_min, norm_max


def get_normalization_scale(norm, norm_min, norm_max, linthresh, linscale):
    if norm is 'linear':
        return colors.Normalize(vmin=norm_min, vmax=norm_max)
    elif norm is 'log':
        if norm_min == 0.0:
            norm_min = 1.e-4
        return colors.LogNorm(vmin=norm_min, vmax=norm_max)
    elif norm is 'symmetric_log':
        return colors.SymLogNorm(linthresh=linthresh, linscale=linscale, vmin=norm_min, vmax=norm_max)
    else:
        raise exc.VisualizeException('The normalization (norm) supplied to the plotter is not a valid string (must be '
                                     'linear | log | symmetric_log')


def get_xylabels(units):
    if units is 'pixels':
        xlabel = 'x (pixels)'
        ylabel = 'y (pixels)'
    elif units is 'arcsec':
        xlabel = 'x (arcsec)'
        ylabel = 'y (arcsec)'
    elif units is 'kpc':
        xlabel = 'x (kpc)'
        ylabel = 'y (kpc)'
    else:
        raise exc.VisualizeException('The units supplied to the plotted are not a valid string (must be pixels | '
                                     'arcsec | kpc)')

    return xlabel, ylabel


def plot_image(array, grid, as_subplot, figsize, aspect, cmap, norm_scale):
    if not as_subplot:
        plt.figure(figsize=figsize)

    if grid is None:
        plt.imshow(array, aspect=aspect, cmap=cmap, norm=norm_scale)
    elif grid is not None:
        plt.imshow(array, aspect=aspect, cmap=cmap, norm=norm_scale,
                   extent=(np.min(grid[:, 0]), np.max(grid[:, 0]), np.min(grid[:, 1]), np.max(grid[:, 1])))


def set_title_and_labels(title, xlabel, ylabel, titlesize, xlabelsize, ylabelsize):
    plt.title(title, fontsize=titlesize)
    plt.xlabel(xlabel, fontsize=xlabelsize)
    plt.ylabel(ylabel, fontsize=ylabelsize)


def set_ticks(array, units, xticks, yticks, xyticksize):
    if units is 'pixels':

        plt.xticks(np.round((array.shape[0] * np.array([0.0, 0.33, 0.66, 0.99]))))
        plt.yticks(np.round((array.shape[1] * np.array([0.0, 0.33, 0.66, 0.99]))))

    elif units is 'arcsec' or units is 'kpc':

        plt.xticks(array.shape[0] * np.array([0.0, 0.33, 0.66, 0.99]), xticks)
        plt.yticks(array.shape[1] * np.array([0.0, 0.33, 0.66, 0.99]), yticks)

    plt.tick_params(labelsize=xyticksize)


def set_colorbar(cb_ticksize):
    cb = plt.colorbar()
    cb.ax.tick_params(labelsize=cb_ticksize)


def plot_grid(grid):
    if grid is not None:
        plt.scatter(x=grid[:, 0], y=grid[:, 1], marker=',')


def output_array(array, output_path, output_filename, output_format):
    if output_format is 'show':
        plt.show()
    elif output_format is 'png':
        plt.savefig(output_path + output_filename + '.png', bbox_inches='tight')
    elif output_format is 'fits':
        hdu = fits.PrimaryHDU()
        hdu.data = array
        hdu.writeto(output_path + output_filename + '.fits')


def output_subplot_array(output_path, output_filename, output_format):
    if output_format is 'show':
        plt.show()
    elif output_format is 'png':
        plt.savefig(output_path + output_filename + '.png', bbox_inches='tight')
    elif output_format is 'fits':
        raise exc.VisualizeException('You cannot output a subplots with format .fits')
