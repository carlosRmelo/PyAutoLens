import numpy as np
from astropy import cosmology as cosmo
from skimage import measure

from autoarray.structures import arrays, grids, visibilities as vis
from autoarray.masked import masked_structures
import autofit as af
from autoastro.util import cosmology_util
from autolens import exc
from autoastro import dimensions as dim
from autolens.util import lens_util


class AbstractPlane(object):
    def __init__(self, redshift, galaxies, cosmology):
        """A plane of galaxies where all galaxies are at the same redshift.

        Parameters
        -----------
        redshift : float or None
            The redshift of the plane.
        galaxies : [Galaxy]
            The list of galaxies in this plane.
        cosmology : astropy.cosmology
            The cosmology associated with the plane, used to convert arc-second coordinates to physical values.
        """

        if redshift is None:

            if not galaxies:
                raise exc.RayTracingException(
                    "A redshift and no galaxies were input to a Plane. A redshift for the Plane therefore cannot be"
                    "determined"
                )
            elif not all(
                [galaxies[0].redshift == galaxy.redshift for galaxy in galaxies]
            ):
                raise exc.RayTracingException(
                    "A redshift and two or more galaxies with different redshifts were input to a Plane. A unique "
                    "Redshift for the Plane therefore cannot be determined"
                )
            else:
                redshift = galaxies[0].redshift

        self.redshift = redshift
        self.galaxies = galaxies
        self.cosmology = cosmology

    @property
    def galaxy_redshifts(self):
        return [galaxy.redshift for galaxy in self.galaxies]

    @property
    def has_light_profile(self):
        return any(list(map(lambda galaxy: galaxy.has_light_profile, self.galaxies)))

    @property
    def has_mass_profile(self):
        return any(list(map(lambda galaxy: galaxy.has_mass_profile, self.galaxies)))

    @property
    def has_pixelization(self):
        return any([galaxy.pixelization for galaxy in self.galaxies])

    @property
    def has_regularization(self):
        return any([galaxy.regularization for galaxy in self.galaxies])

    @property
    def galaxies_with_pixelization(self):
        return list(filter(lambda galaxy: galaxy.has_pixelization, self.galaxies))

    @property
    def galaxies_with_regularization(self):
        return list(filter(lambda galaxy: galaxy.has_regularization, self.galaxies))

    @property
    def pixelization(self):

        if len(self.galaxies_with_pixelization) == 0:
            return None
        if len(self.galaxies_with_pixelization) == 1:
            return self.galaxies_with_pixelization[0].pixelization
        elif len(self.galaxies_with_pixelization) > 1:
            raise exc.PixelizationException(
                "The number of galaxies with pixelizations in one plane is above 1"
            )

    @property
    def regularization(self):

        if len(self.galaxies_with_regularization) == 0:
            return None
        if len(self.galaxies_with_regularization) == 1:
            return self.galaxies_with_regularization[0].regularization
        elif len(self.galaxies_with_regularization) > 1:
            raise exc.PixelizationException(
                "The number of galaxies with regularizations in one plane is above 1"
            )

    @property
    def hyper_galaxy_image_of_galaxy_with_pixelization(self):
        galaxies_with_pixelization = self.galaxies_with_pixelization
        if galaxies_with_pixelization:
            return galaxies_with_pixelization[0].hyper_galaxy_image

    @property
    def has_hyper_galaxy(self):
        return any(list(map(lambda galaxy: galaxy.has_hyper_galaxy, self.galaxies)))

    @property
    def centres_of_galaxy_mass_profiles(self):

        galaxies_with_mass_profiles = [
            galaxy for galaxy in self.galaxies if galaxy.has_mass_profile
        ]

        mass_profile_centres = [[] for _ in range(len(galaxies_with_mass_profiles))]

        for galaxy_index, galaxy in enumerate(galaxies_with_mass_profiles):
            mass_profile_centres[galaxy_index] = [
                profile.centre for profile in galaxy.mass_profiles
            ]
        return mass_profile_centres

    @property
    def axis_ratios_of_galaxy_mass_profiles(self):
        galaxies_with_mass_profiles = [
            galaxy for galaxy in self.galaxies if galaxy.has_mass_profile
        ]

        mass_profile_axis_ratios = [[] for _ in range(len(galaxies_with_mass_profiles))]

        for galaxy_index, galaxy in enumerate(galaxies_with_mass_profiles):
            mass_profile_axis_ratios[galaxy_index] = [
                profile.axis_ratio for profile in galaxy.mass_profiles
            ]
        return mass_profile_axis_ratios

    @property
    def phis_of_galaxy_mass_profiles(self):

        galaxies_with_mass_profiles = [
            galaxy for galaxy in self.galaxies if galaxy.has_mass_profile
        ]

        mass_profile_phis = [[] for _ in range(len(galaxies_with_mass_profiles))]

        for galaxy_index, galaxy in enumerate(galaxies_with_mass_profiles):
            mass_profile_phis[galaxy_index] = [
                profile.phi for profile in galaxy.mass_profiles
            ]
        return mass_profile_phis


class AbstractPlaneCosmology(AbstractPlane):
    def __init__(self, redshift, galaxies, cosmology):

        super(AbstractPlaneCosmology, self).__init__(
            redshift=redshift, galaxies=galaxies, cosmology=cosmology
        )

    @property
    def arcsec_per_kpc(self):
        return cosmology_util.arcsec_per_kpc_from_redshift_and_cosmology(
            redshift=self.redshift, cosmology=self.cosmology
        )

    @property
    def kpc_per_arcsec(self):
        return 1.0 / self.arcsec_per_kpc

    def angular_diameter_distance_to_earth_in_units(self, unit_length="arcsec"):
        return cosmology_util.angular_diameter_distance_to_earth_from_redshift_and_cosmology(
            redshift=self.redshift, cosmology=self.cosmology, unit_length=unit_length
        )

    def cosmic_average_density_in_units(
        self, unit_length="arcsec", unit_mass="solMass"
    ):
        return cosmology_util.cosmic_average_density_from_redshift_and_cosmology(
            redshift=self.redshift,
            cosmology=self.cosmology,
            unit_length=unit_length,
            unit_mass=unit_mass,
        )


class AbstractPlaneLensing(AbstractPlaneCosmology):
    def __init__(self, redshift, galaxies, cosmology):
        super(AbstractPlaneCosmology, self).__init__(
            redshift=redshift, galaxies=galaxies, cosmology=cosmology
        )

    def profile_image_from_grid(self, grid):
        """Compute the profile-image plane image of the list of galaxies of the plane's sub-grid, by summing the
        individual images of each galaxy's light profile.

        The image is calculated on the sub-grid and binned-up to the original grid by taking the mean
        value of every set of sub-pixels, provided the *returned_binned_sub_grid* bool is *True*.

        If the plane has no galaxies (or no galaxies have mass profiles) an arrays of all zeros the shape of the plane's
        sub-grid is returned.

        Parameters
        -----------

        """
        if self.galaxies:
            profile_image = sum(
                map(
                    lambda galaxy: galaxy.profile_image_from_grid(grid=grid),
                    self.galaxies,
                )
            )
            return grid.mapping.array_from_sub_array_1d(sub_array_1d=profile_image)
        else:
            return grid.mapping.array_from_sub_array_1d(
                sub_array_1d=np.zeros((grid.sub_shape_1d,))
            )

    def profile_images_of_galaxies_from_grid(self, grid):
        return list(
            map(lambda galaxy: galaxy.profile_image_from_grid(grid=grid), self.galaxies)
        )

    def convergence_from_grid(self, grid):
        """Compute the convergence of the list of galaxies of the plane's sub-grid, by summing the individual convergences \
        of each galaxy's mass profile.

        The convergence is calculated on the sub-grid and binned-up to the original grid by taking the mean
        value of every set of sub-pixels, provided the *returned_binned_sub_grid* bool is *True*.

        If the plane has no galaxies (or no galaxies have mass profiles) an arrays of all zeros the shape of the plane's
        sub-grid is returned.

        Parameters
        -----------
        grid : Grid
            The grid (or sub) of (y,x) arc-second coordinates at the centre of every unmasked pixel which the \
            potential is calculated on.
        galaxies : [galaxy.Galaxy]
            The galaxies whose mass profiles are used to compute the surface densities.
        """
        if self.galaxies:
            convergence = sum(
                map(lambda g: g.convergence_from_grid(grid=grid), self.galaxies)
            )
            return grid.mapping.array_from_sub_array_1d(sub_array_1d=convergence)
        else:
            return grid.mapping.array_from_sub_array_1d(
                sub_array_1d=np.full((grid.sub_shape_1d), 0.0)
            )

    def potential_from_grid(self, grid):
        """Compute the potential of the list of galaxies of the plane's sub-grid, by summing the individual potentials \
        of each galaxy's mass profile.

        The potential is calculated on the sub-grid and binned-up to the original grid by taking the mean
        value of every set of sub-pixels, provided the *returned_binned_sub_grid* bool is *True*.

        If the plane has no galaxies (or no galaxies have mass profiles) an arrays of all zeros the shape of the plane's
        sub-grid is returned.

        Parameters
        -----------
        grid : Grid
            The grid (or sub) of (y,x) arc-second coordinates at the centre of every unmasked pixel which the \
            potential is calculated on.
        galaxies : [galaxy.Galaxy]
            The galaxies whose mass profiles are used to compute the surface densities.
        """
        if self.galaxies:
            potential = sum(
                map(lambda g: g.potential_from_grid(grid=grid), self.galaxies)
            )
            return grid.mapping.array_from_sub_array_1d(sub_array_1d=potential)
        else:
            return grid.mapping.array_from_sub_array_1d(
                sub_array_1d=np.full((grid.sub_shape_1d), 0.0)
            )

    def deflections_from_grid(self, grid):
        if self.galaxies:
            deflections = sum(
                map(lambda g: g.deflections_from_grid(grid=grid), self.galaxies)
            )
            return grid.mapping.grid_from_sub_grid_1d(sub_grid_1d=deflections)
        else:
            return grid.mapping.grid_from_sub_grid_1d(
                sub_grid_1d=np.full((grid.sub_shape_1d, 2), 0.0)
            )

    def traced_grid_from_grid(self, grid):
        """Trace this plane's grid_stacks to the next plane, using its deflection angles."""

        traced_grid = grid - self.deflections_from_grid(grid=grid)
        return grid.mapping.grid_from_sub_grid_1d(sub_grid_1d=traced_grid)

    def deflections_via_potential_from_grid(self, grid):
        potential = self.potential_from_grid(grid=grid)

        deflections_y_2d = np.gradient(potential.in_2d, grid.in_2d[:, 0, 0], axis=0)
        deflections_x_2d = np.gradient(potential.in_2d, grid.in_2d[0, :, 1], axis=1)

        return grid.mapping.grid_from_sub_grid_2d(
            sub_grid_2d=np.stack((deflections_y_2d, deflections_x_2d), axis=-1)
        )

    def jacobian_a11_from_grid(self, grid):

        deflections = self.deflections_from_grid(grid=grid)

        return grid.mapping.array_from_sub_array_2d(
            sub_array_2d=1.0
            - np.gradient(deflections.in_2d[:, :, 1], grid.in_2d[0, :, 1], axis=1)
        )

    def jacobian_a12_from_grid(self, grid):

        deflections = self.deflections_from_grid(grid=grid)

        return grid.mapping.array_from_sub_array_2d(
            sub_array_2d=-1.0
            * np.gradient(deflections.in_2d[:, :, 1], grid.in_2d[:, 0, 0], axis=0)
        )

    def jacobian_a21_from_grid(self, grid):

        deflections = self.deflections_from_grid(grid=grid)

        return grid.mapping.array_from_sub_array_2d(
            sub_array_2d=-1.0
            * np.gradient(deflections.in_2d[:, :, 0], grid.in_2d[0, :, 1], axis=1)
        )

    def jacobian_a22_from_grid(self, grid):

        deflections = self.deflections_from_grid(grid=grid)

        return grid.mapping.array_from_sub_array_2d(
            sub_array_2d=1
            - np.gradient(deflections.in_2d[:, :, 0], grid.in_2d[:, 0, 0], axis=0)
        )

    def jacobian_from_grid(self, grid):

        a11 = self.jacobian_a11_from_grid(grid=grid)

        a12 = self.jacobian_a12_from_grid(grid=grid)

        a21 = self.jacobian_a21_from_grid(grid=grid)

        a22 = self.jacobian_a22_from_grid(grid=grid)

        return [[a11, a12], [a21, a22]]

    def convergence_via_jacobian_from_grid(self, grid):

        jacobian = self.jacobian_from_grid(grid=grid)

        convergence = 1 - 0.5 * (jacobian[0][0] + jacobian[1][1])

        return grid.mapping.array_from_sub_array_1d(sub_array_1d=convergence)

    def shear_via_jacobian_from_grid(self, grid):

        jacobian = self.jacobian_from_grid(grid=grid)

        gamma_1 = 0.5 * (jacobian[1][1] - jacobian[0][0])
        gamma_2 = -0.5 * (jacobian[0][1] + jacobian[1][0])

        return grid.mapping.array_from_sub_array_1d(
            sub_array_1d=(gamma_1 ** 2 + gamma_2 ** 2) ** 0.5
        )

    def tangential_eigen_value_from_grid(self, grid):

        convergence = self.convergence_via_jacobian_from_grid(grid=grid)

        shear = self.shear_via_jacobian_from_grid(grid=grid)

        return grid.mapping.array_from_sub_array_1d(
            sub_array_1d=1 - convergence - shear
        )

    def radial_eigen_value_from_grid(self, grid):

        convergence = self.convergence_via_jacobian_from_grid(grid=grid)

        shear = self.shear_via_jacobian_from_grid(grid=grid)

        return grid.mapping.array_from_sub_array_1d(
            sub_array_1d=1 - convergence + shear
        )

    def magnification_from_grid(self, grid):

        jacobian = self.jacobian_from_grid(grid=grid)

        det_jacobian = jacobian[0][0] * jacobian[1][1] - jacobian[0][1] * jacobian[1][0]

        return grid.mapping.array_from_sub_array_1d(sub_array_1d=1 / det_jacobian)

    def tangential_critical_curve_from_grid(self, grid):

        tangential_eigen_values = self.tangential_eigen_value_from_grid(grid=grid)

        tangential_critical_curve_indices = measure.find_contours(
            tangential_eigen_values.in_2d, 0
        )

        if len(tangential_critical_curve_indices) == 0:
            return []

        tangential_critical_curve = grid.geometry.grid_arcsec_from_grid_pixels_1d_for_marching_squares(
            grid_pixels_1d=tangential_critical_curve_indices[0],
            shape_2d=tangential_eigen_values.sub_shape_2d,
        )

        return grids.GridIrregular(grid=tangential_critical_curve)

    def radial_critical_curve_from_grid(self, grid):

        radial_eigen_values = self.radial_eigen_value_from_grid(grid=grid)

        radial_critical_curve_indices = measure.find_contours(
            radial_eigen_values.in_2d, 0
        )

        if len(radial_critical_curve_indices) == 0:
            return []

        radial_critical_curve = grid.geometry.grid_arcsec_from_grid_pixels_1d_for_marching_squares(
            grid_pixels_1d=radial_critical_curve_indices[0],
            shape_2d=radial_eigen_values.sub_shape_2d,
        )

        return grids.GridIrregular(grid=radial_critical_curve)

    def tangential_caustic_from_grid(self, grid):

        tangential_critical_curve = self.tangential_critical_curve_from_grid(grid=grid)

        if len(tangential_critical_curve) == 0:
            return []

        deflections_1d = self.deflections_from_grid(grid=tangential_critical_curve)

        return tangential_critical_curve - deflections_1d

    def radial_caustic_from_grid(self, grid):

        radial_critical_curve = self.radial_critical_curve_from_grid(grid=grid)

        if len(radial_critical_curve) == 0:
            return []

        deflections_critical_curve = self.deflections_from_grid(
            grid=radial_critical_curve
        )

        return radial_critical_curve - deflections_critical_curve

    def critical_curves_from_grid(self, grid):
        return [
            self.tangential_critical_curve_from_grid(grid=grid),
            self.radial_critical_curve_from_grid(grid=grid),
        ]

    def caustics_from_grid(self, grid):
        return [
            self.tangential_caustic_from_grid(grid=grid),
            self.radial_caustic_from_grid(grid=grid),
        ]

    def luminosities_of_galaxies_within_circles_in_units(
        self, radius: dim.Length, unit_luminosity="eps", exposure_time=None
    ):
        """Compute the total luminosity of all galaxies in this plane within a circle of specified radius.

        See *galaxy.light_within_circle* and *light_profiles.light_within_circle* for details \
        of how this is performed.

        Parameters
        ----------
        radius : float
            The radius of the circle to compute the dimensionless mass within.
        unit_luminosity : str
            The units the luminosity is returned in (eps | counts).
        exposure_time : float
            The exposure time of the observation, which converts luminosity from electrons per second units to counts.
        """
        return list(
            map(
                lambda galaxy: galaxy.luminosity_within_circle_in_units(
                    radius=radius,
                    unit_luminosity=unit_luminosity,
                    exposure_time=exposure_time,
                    cosmology=self.cosmology,
                ),
                self.galaxies,
            )
        )

    def luminosities_of_galaxies_within_ellipses_in_units(
        self, major_axis: dim.Length, unit_luminosity="eps", exposure_time=None
    ):
        """
        Compute the total luminosity of all galaxies in this plane within a ellipse of specified major-axis.

        The value returned by this integral is dimensionless, and a conversion factor can be specified to convert it \
        to a physical value (e.g. the photometric zeropoint).

        See *galaxy.light_within_ellipse* and *light_profiles.light_within_ellipse* for details
        of how this is performed.

        Parameters
        ----------
        major_axis : float
            The major-axis radius of the ellipse.
        unit_luminosity : str
            The units the luminosity is returned in (eps | counts).
        exposure_time : float
            The exposure time of the observation, which converts luminosity from electrons per second units to counts.
        """
        return list(
            map(
                lambda galaxy: galaxy.luminosity_within_ellipse_in_units(
                    major_axis=major_axis,
                    unit_luminosity=unit_luminosity,
                    exposure_time=exposure_time,
                    cosmology=self.cosmology,
                ),
                self.galaxies,
            )
        )

    def masses_of_galaxies_within_circles_in_units(
        self, radius: dim.Length, unit_mass="solMass", redshift_source=None
    ):
        """Compute the total mass of all galaxies in this plane within a circle of specified radius.

        See *galaxy.angular_mass_within_circle* and *mass_profiles.angular_mass_within_circle* for details
        of how this is performed.

        Parameters
        ----------
        redshift_source
        radius : float
            The radius of the circle to compute the dimensionless mass within.
        unit_mass : str
            The units the mass is returned in (angular | solMass).

        """
        return list(
            map(
                lambda galaxy: galaxy.mass_within_circle_in_units(
                    radius=radius,
                    unit_mass=unit_mass,
                    redshift_source=redshift_source,
                    cosmology=self.cosmology,
                ),
                self.galaxies,
            )
        )

    def masses_of_galaxies_within_ellipses_in_units(
        self, major_axis: dim.Length, unit_mass="solMass", redshift_source=None
    ):
        """Compute the total mass of all galaxies in this plane within a ellipse of specified major-axis.

        See *galaxy.angular_mass_within_ellipse* and *mass_profiles.angular_mass_within_ellipse* for details \
        of how this is performed.

        Parameters
        ----------
        redshift_source
        unit_mass
        major_axis : float
            The major-axis radius of the ellipse.

        """
        return list(
            map(
                lambda galaxy: galaxy.mass_within_ellipse_in_units(
                    major_axis=major_axis,
                    unit_mass=unit_mass,
                    redshift_source=redshift_source,
                    cosmology=self.cosmology,
                ),
                self.galaxies,
            )
        )

    def einstein_radius_in_units(self, unit_length="arcsec"):

        if self.has_mass_profile:
            return sum(
                filter(
                    None,
                    list(
                        map(
                            lambda galaxy: galaxy.einstein_radius_in_units(
                                unit_length=unit_length, cosmology=self.cosmology
                            ),
                            self.galaxies,
                        )
                    ),
                )
            )

    def einstein_mass_in_units(self, unit_mass="solMass", redshift_source=None):

        if self.has_mass_profile:
            return sum(
                filter(
                    None,
                    list(
                        map(
                            lambda galaxy: galaxy.einstein_mass_in_units(
                                unit_mass=unit_mass,
                                redshift_source=redshift_source,
                                cosmology=self.cosmology,
                            ),
                            self.galaxies,
                        )
                    ),
                )
            )


class AbstractPlaneData(AbstractPlaneLensing):
    def __init__(self, redshift, galaxies, cosmology):

        super(AbstractPlaneData, self).__init__(
            redshift=redshift, galaxies=galaxies, cosmology=cosmology
        )

    def blurred_profile_image_from_grid_and_psf(self, grid, psf, blurring_grid):

        profile_image = self.profile_image_from_grid(grid=grid)

        blurring_image = self.profile_image_from_grid(grid=blurring_grid)

        return psf.convolved_array_from_array_2d_and_mask(
            array_2d=profile_image.in_2d_binned + blurring_image.in_2d_binned,
            mask=grid.mask,
        )

    def blurred_profile_images_of_galaxies_from_grid_and_psf(
        self, grid, psf, blurring_grid
    ):
        return [
            galaxy.blurred_profile_image_from_grid_and_psf(
                grid=grid, psf=psf, blurring_grid=blurring_grid
            )
            for galaxy in self.galaxies
        ]

    def blurred_profile_image_from_grid_and_convolver(
        self, grid, convolver, blurring_grid
    ):

        profile_image = self.profile_image_from_grid(grid=grid)

        blurring_image = self.profile_image_from_grid(grid=blurring_grid)

        return convolver.convolved_image_from_image_and_blurring_image(
            image=profile_image, blurring_image=blurring_image
        )

    def blurred_profile_images_of_galaxies_from_grid_and_convolver(
        self, grid, convolver, blurring_grid
    ):
        return [
            galaxy.blurred_profile_image_from_grid_and_convolver(
                grid=grid, convolver=convolver, blurring_grid=blurring_grid
            )
            for galaxy in self.galaxies
        ]

    def profile_visibilities_from_grid_and_transformer(self, grid, transformer):

        if self.galaxies:
            profile_image = self.profile_image_from_grid(grid=grid)
            return transformer.visibilities_from_image(image=profile_image)
        else:
            return vis.Visibilities.zeros(
                shape_1d=(transformer.uv_wavelengths.shape[0],)
            )

    def profile_visibilities_of_galaxies_from_grid_and_transformer(
        self, grid, transformer
    ):
        return [
            galaxy.profile_visibilities_from_grid_and_transformer(
                grid=grid, transformer=transformer
            )
            for galaxy in self.galaxies
        ]

    def sparse_image_plane_grid_from_grid(self, grid):

        if not self.has_pixelization:
            return None

        hyper_galaxy_image = self.hyper_galaxy_image_of_galaxy_with_pixelization

        return self.pixelization.sparse_grid_from_grid(
            grid=grid, hyper_image=hyper_galaxy_image
        )

    def mapper_from_grid_and_sparse_grid(
        self, grid, sparse_grid, inversion_uses_border=False
    ):

        galaxies_with_pixelization = list(
            filter(lambda galaxy: galaxy.pixelization is not None, self.galaxies)
        )

        if len(galaxies_with_pixelization) == 0:
            return None
        if len(galaxies_with_pixelization) == 1:

            pixelization = galaxies_with_pixelization[0].pixelization

            return pixelization.mapper_from_grid_and_sparse_grid(
                grid=grid,
                sparse_grid=sparse_grid,
                inversion_uses_border=inversion_uses_border,
                hyper_image=galaxies_with_pixelization[0].hyper_galaxy_image,
            )

        elif len(galaxies_with_pixelization) > 1:
            raise exc.PixelizationException(
                "The number of galaxies with pixelizations in one plane is above 1"
            )

    def plane_image_from_grid(self, grid):
        return lens_util.plane_image_of_galaxies_from_grid(
            shape=grid.mask.shape,
            grid=grid.geometry.unmasked_grid,
            galaxies=self.galaxies,
        )

    def hyper_noise_map_from_noise_map(self, noise_map):
        hyper_noise_maps = self.hyper_noise_maps_of_galaxies_from_noise_map(
            noise_map=noise_map
        )
        return sum(hyper_noise_maps)

    def hyper_noise_maps_of_galaxies_from_noise_map(self, noise_map):
        """For a contribution map and noise-map, use the model hyper_galaxy galaxies to compute a hyper noise-map.

        Parameters
        -----------
        noise_map : imaging.NoiseMap or ndarray
            An arrays describing the RMS standard deviation error in each pixel, preferably in units of electrons per
            second.
        """
        hyper_noise_maps = []

        for galaxy in self.galaxies:
            if galaxy.hyper_galaxy is not None:

                hyper_noise_map_1d = galaxy.hyper_galaxy.hyper_noise_map_from_hyper_images_and_noise_map(
                    noise_map=noise_map,
                    hyper_model_image=galaxy.hyper_model_image,
                    hyper_galaxy_image=galaxy.hyper_galaxy_image,
                )

                hyper_noise_maps.append(hyper_noise_map_1d)

            else:

                hyper_noise_maps.append(masked_structures.MaskedArray.zeros(mask=noise_map.mask))

        return hyper_noise_maps

    @property
    def contribution_maps_of_galaxies(self):

        contribution_maps = []

        for galaxy in self.galaxies:

            if galaxy.hyper_galaxy is not None:

                contribution_map = galaxy.hyper_galaxy.contribution_map_from_hyper_images(
                    hyper_model_image=galaxy.hyper_model_image,
                    hyper_galaxy_image=galaxy.hyper_galaxy_image,
                )

                contribution_maps.append(contribution_map)

            else:

                contribution_maps.append(None)

        return contribution_maps

    @property
    def yticks(self):
        """Compute the yticks labels of this grid, used for plotting the y-axis ticks when visualizing an image \
        """
        return np.linspace(np.amin(self.grid[:, 0]), np.amax(self.grid[:, 0]), 4)

    @property
    def xticks(self):
        """Compute the xticks labels of this grid, used for plotting the x-axis ticks when visualizing an \
        image"""
        return np.linspace(np.amin(self.grid[:, 1]), np.amax(self.grid[:, 1]), 4)


class Plane(AbstractPlaneData):
    def __init__(self, redshift=None, galaxies=None, cosmology=cosmo.Planck15):

        super(Plane, self).__init__(
            redshift=redshift, galaxies=galaxies, cosmology=cosmology
        )

    # noinspection PyUnusedLocal
    def summarize_in_units(
        self,
        radii,
        whitespace=80,
        unit_length="arcsec",
        unit_luminosity="eps",
        unit_mass="solMass",
        redshift_source=None,
        **kwargs
    ):

        summary = ["Plane\n"]
        prefix_plane = ""

        summary += [
            af.text_util.label_and_value_string(
                label=prefix_plane + "redshift",
                value=self.redshift,
                whitespace=whitespace,
                format_string="{:.2f}",
            )
        ]

        summary += [
            af.text_util.label_and_value_string(
                label=prefix_plane + "kpc_per_arcsec",
                value=self.kpc_per_arcsec,
                whitespace=whitespace,
                format_string="{:.2f}",
            )
        ]

        angular_diameter_distance_to_earth = self.angular_diameter_distance_to_earth_in_units(
            unit_length=unit_length
        )

        summary += [
            af.text_util.label_and_value_string(
                label=prefix_plane + "angular_diameter_distance_to_earth",
                value=angular_diameter_distance_to_earth,
                whitespace=whitespace,
                format_string="{:.2f}",
            )
        ]

        for galaxy in self.galaxies:
            summary += ["\n"]
            summary += galaxy.summarize_in_units(
                radii=radii,
                whitespace=whitespace,
                unit_length=unit_length,
                unit_luminosity=unit_luminosity,
                unit_mass=unit_mass,
                redshift_source=redshift_source,
                cosmology=self.cosmology,
            )

        return summary


class PlanePositions(object):
    def __init__(
        self, redshift, galaxies, positions, compute_deflections=True, cosmology=None
    ):
        """A plane represents a set of galaxies at a given redshift in a ray-tracer_normal and the positions of image-plane \
        coordinates which mappers close to one another in the source-plane.

        Parameters
        -----------
        galaxies : [Galaxy]
            The list of lens galaxies in this plane.
        positions : [[[]]]
            The (y,x) arc-second coordinates of image-plane pixels which (are expected to) mappers to the same
            location(s) in the final source-plane.
        compute_deflections : bool
            If true, the deflection-angles of this plane's coordinates are calculated use its galaxy's mass-profiles.
        """

        self.redshift = redshift
        self.galaxies = galaxies
        self.positions = positions

        if compute_deflections:

            def calculate_deflections(pos):
                return sum(
                    map(lambda galaxy: galaxy.deflections_from_grid(pos), galaxies)
                )

            self.deflections = list(
                map(lambda pos: calculate_deflections(pos), self.positions)
            )

        self.cosmology = cosmology

    def trace_to_next_plane(self):
        """Trace the positions to the next plane."""
        return list(
            map(
                lambda positions, deflections: np.subtract(positions, deflections),
                self.positions,
                self.deflections,
            )
        )


class PlaneImage(object):
    def __init__(self, array, grid):
        self.array = array
        self.grid = grid

    @property
    def xticks(self):
        return self.array.mask.geometry.xticks

    @property
    def yticks(self):
        return self.array.mask.geometry.yticks
