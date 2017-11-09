import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np

def make_2d_histogram(xx, yy, dx, dy):
    """
    returns indices and counts of unique points on the map
    """
    i_color1 = np.round(xx/dx).astype(int)
    i_color2 = np.round(yy/dy).astype(int)
    dex_reverse = np.array([i_color1, i_color2])
    dex_arr = dex_reverse.transpose()
    # see http://stackoverflow.com/questions/16970982/find-unique-rows-in-numpy-array
    dex_raw = np.ascontiguousarray(dex_arr).view(np.dtype((np.void, dex_arr.dtype.itemsize*dex_arr.shape[1])))
    _, unique_rows, unique_counts = np.unique(dex_raw, return_index=True, return_counts=True)

    return unique_rows, unique_counts


def plot_color(xx, yy, dx, dy):
    dexes, cts = make_2d_histogram(xx, yy, dx, dy)
    sorted_dex = np.argsort(cts)
    dexes = dexes[sorted_dex]
    cts = cts[sorted_dex]
    plt.scatter(xx[dexes], yy[dexes], c=cts, s=5,
                cmap=plt.cm.gist_ncar, edgecolor='')

    plt.colorbar()


def plot_color_mesh(xx, yy, dx, dy, vmin=None, vmax=None):
    i_x_arr = np.round((xx-xx.min())/dx).astype(int)
    i_y_arr = np.round((yy-yy.min())/dy).astype(int)
    new_x = i_x_arr*dx
    new_y = i_y_arr*dy
    dex_list, ct_list = make_2d_histogram(new_x, new_y, dx, dy)

    if i_x_arr.min()<0 or i_y_arr.min()<0:
        raise RuntimeError('negative dex %e %d %e %d' %
                           (xx.min(), i_x_arr.min(), yy.min(), i_y_arr.min()))

    x_mesh=np.arange(xx.min(),xx.max()+0.1,dx)
    y_mesh=np.arange(yy.min(),yy.max()+0.1,dy)
    x_mesh,y_mesh = np.meshgrid(x_mesh,y_mesh,indexing='xy')
    z_mesh = np.zeros(shape=x_mesh.shape, dtype=int)
    ct_1000b = 0

    for dex, ct in zip(dex_list, ct_list):
        ix = i_x_arr[dex]
        iy = i_y_arr[dex]
        z_mesh[iy][ix] += ct

    z_mesh = np.ma.masked_where(z_mesh==0,z_mesh)
    plt.pcolormesh(x_mesh,y_mesh,z_mesh, vmin=vmin, vmax=vmax)
                   #norm=matplotlib.colors.LogNorm(vmin=1.0,
                   #                               vmax=1.2e6))
    #plt.colorbar(label='sources per pixel')
    plt.colorbar()


dtype = np.dtype([('rv', float), ('av', float), ('ebv', float),
                  ('dist', float), ('du', float), ('dg', float),
                  ('dr', float), ('di', float), ('dz', float),
                  ('dy', float)])

mag_data = np.genfromtxt('Rv_vs_magdist.txt', dtype=dtype)

valid = np.where(mag_data['rv'] < 30.0)
rv = mag_data['rv'][valid]

plt.figsize = (30,30)

for i_fig, mag in enumerate(('u', 'g', 'r', 'i', 'z', 'y')):
    plt.subplot(3,2,i_fig+1)

    dmag = mag_data['d%s' % mag][valid]

    for_lim = dmag[np.where(rv<10.0)]

    dmag_min = for_lim.min()
    dmag_max = for_lim.max()

    plot_color_mesh(rv, dmag, 0.1, 0.02)
    if i_fig == 0:
        plt.xlabel('Rv', fontsize=9)
        plt.ylabel('SED-Galacticus', fontsize=9)
    plt.title('%s' % mag, fontsize=7)
    plt.ylim(dmag_min, dmag_max)
    #if mag == 'u' or mag == 'g':
    #    plt.ylim((-2.0,1.0))
    #else:
    #    plt.ylim((-0.25, 0.25))

    rounded_min = np.round(dmag_min, decimals=1)
    rounded_max = np.round(dmag_max, decimals=1)
    yticks = np.arange(rounded_min, rounded_max+0.05, 0.1)
    if mag != 'u':
        zero_tick = np.argmin(np.abs(yticks))
        ylabels = ['' if (np.abs(iy-zero_tick)%5!=0 and iy!=0 and iy!=len(yticks)-1) else' %.1f' % yticks[iy]
                   for iy in range(len(yticks))]
    else:
        yticks = [yy for yy in yticks if yy%0.5<0.0001 ]
        ylabels = ['%.1f' % yticks[iy] for iy in range(len(yticks))]

    plt.yticks(yticks,ylabels)

plt.tight_layout()
plt.savefig('rv_dmag_dist.png')
plt.close()
