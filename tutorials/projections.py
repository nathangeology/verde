"""
Geographic Coordinates
======================

Most gridders and processing methods in Verde operate under the assumption that the data
coordinates are Cartesian. To process data in geographic (longitude and latitude)
coordinates, we must first project them. There are different ways of doing this in
Python but most of them rely on the `PROJ library <https://proj4.org/>`__. We'll use
`pyproj <https://github.com/jswhit/pyproj>`__ to access PROJ directly and handle the
projection operations.
"""
import pyproj
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import verde as vd

########################################################################################
# With pyproj, we can create functions that will project our coordinates to and from
# different coordinate systems. For our Baja California bathymetry data, we'll use a
# Mercator projection.

data = vd.datasets.fetch_baja_bathymetry()
# We're choosing the latitude of true scale as the mean latitude of our dataset.
projection = pyproj.Proj(proj="merc", lat_ts=data.latitude.mean())

########################################################################################
# The Proj object is a callable (meaning that it behaves like a function) that will take
# longitude and latitude and return easting and northing coordinates.

# pyproj doesn't play well with Pandas so we need to convert to numpy arrays
proj_coords = projection(data.longitude.values, data.latitude.values)
print(proj_coords)

########################################################################################
# We can plot our projected coordinates using matplotlib.

plt.figure(figsize=(7, 6))
plt.title("Projected coordinates of bathymetry measurements")
# Plot the bathymetry data locations as black dots
plt.plot(proj_coords[0], proj_coords[1], ".k", markersize=0.5)
plt.xlabel("Easting (m)")
plt.ylabel("Northing (m)")
plt.gca().set_aspect("equal")
plt.tight_layout()
plt.show()

########################################################################################
# Cartesian grids
# ---------------
#
# Now we can use :class:`verde.BlockReduce` and :class:`verde.Spline` on our projected
# coordinates. We'll specify the desired grid spacing as degrees and convert it to
# Cartesian using the 1 degree approx. 111 km rule-of-thumb.
spacing = 10 / 60
reducer = vd.BlockReduce(np.median, spacing=spacing * 111e3)
filter_coords, filter_bathy = reducer.filter(proj_coords, data.bathymetry_m)
spline = vd.Spline().fit(filter_coords, filter_bathy)

########################################################################################
# If we now call :meth:`verde.Spline.grid` we'll get back a grid evenly spaced in
# projected Cartesian coordinates.
grid = spline.grid(spacing=spacing * 111e3, data_names=["bathymetry"])
print("Cartesian grid:")
print(grid)

########################################################################################
# We'll mask our grid using :func:`verde.distance_mask` to get rid of all the spurious
# solutions far away from the data points.
grid = vd.distance_mask(proj_coords, maxdist=30e3, grid=grid)

plt.figure(figsize=(7, 6))
plt.title("Gridded bathymetry in Cartesian coordinates")
plt.pcolormesh(grid.easting, grid.northing, grid.bathymetry, cmap="viridis", vmax=0)
plt.colorbar().set_label("bathymetry (m)")
plt.plot(filter_coords[0], filter_coords[1], ".k", markersize=0.5)
plt.xlabel("Easting (m)")
plt.ylabel("Northing (m)")
plt.gca().set_aspect("equal")
plt.tight_layout()
plt.show()


########################################################################################
# Geographic grids
# ----------------
#
# The Cartesian grid that we generated won't be evenly spaced if we convert the
# coordinates back to geographic latitude and longitude. Verde gridders allow you to
# generate an evenly spaced grid in geographic coordinates through the ``projection``
# argument of the :meth:`~verde.base.BaseGridder.grid` method.
#
# By providing a projection function (like our pyproj ``projection`` object), Verde will
# generate coordinates for a regular grid and then pass them through the projection
# function before predicting data values. This way, you can generate a grid in a
# coordinate system other than the one you used to fit the spline.

# Get the geographic bounding region of the data
region = vd.get_region((data.longitude, data.latitude))
print("Data region in degrees:", region)

# Specify the region and spacing in degrees and a projection function
grid_geo = spline.grid(
    region=region,
    spacing=spacing,
    projection=projection,
    dims=["latitude", "longitude"],
    data_names=["bathymetry"],
)
print("Geographic grid:")
print(grid_geo)

########################################################################################
# Notice that grid has longitude and latitude coordinates and slightly different number
# of points than the Cartesian grid.
#
# The :func:`verde.distance_mask` function also supports the ``projection`` argument and
# will project the coordinates before calculating distances.

grid_geo = vd.distance_mask(
    (data.longitude, data.latitude), maxdist=30e3, grid=grid_geo, projection=projection
)

########################################################################################
# Now we can use the Cartopy library to plot our geographic grid.

plt.figure(figsize=(7, 6))
ax = plt.axes(projection=ccrs.Mercator())
ax.set_title("Geographic grid of bathymetry")
pc = ax.pcolormesh(
    grid_geo.longitude,
    grid_geo.latitude,
    grid_geo.bathymetry,
    transform=ccrs.PlateCarree(),
    vmax=0,
    zorder=-1,
)
plt.colorbar(pc).set_label("meters")
vd.datasets.setup_baja_bathymetry_map(ax, land=None)
plt.tight_layout()
plt.show()
