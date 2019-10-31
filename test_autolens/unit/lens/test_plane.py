import numpy as np
import pytest
from astropy import cosmology as cosmo
from skimage import measure

import autoastro as am
import autolens as al
from autolens.lens import plane
from autolens import exc

from test_autoarray.mock import mock_inversion
from test_autoastro.mock.mock_cosmology import MockCosmology

planck = cosmo.Planck15


def critical_curve_via_magnification_from_plane_and_grid(plane, grid):
    magnification = plane.magnification_from_grid(grid=grid)

    inverse_magnification = 1 / magnification

    critical_curves_indices = measure.find_contours(inverse_magnification.in_2d, 0)

    no_critical_curves = len(critical_curves_indices)
    contours = []
    critical_curves = []

    for jj in np.arange(no_critical_curves):
        contours.append(critical_curves_indices[jj])
        contour_x, contour_y = contours[jj].T
        pixel_coord = np.stack((contour_x, contour_y), axis=-1)

        critical_curve = grid.geometry.grid_arcsec_from_grid_pixels_1d_for_marching_squares(
            grid_pixels_1d=pixel_coord, shape_2d=magnification.sub_shape_2d
        )

        critical_curve = al.grid_irregular.manual_1d(grid=critical_curve)

        critical_curves.append(critical_curve)

    return critical_curves


def caustics_via_magnification_from_plane_and_grid(plane, grid):
    caustics = []

    critical_curves = critical_curve_via_magnification_from_plane_and_grid(
        plane=plane, grid=grid
    )

    for i in range(len(critical_curves)):
        critical_curve = critical_curves[i]

        deflections_1d = plane.deflections_from_grid(grid=critical_curve)

        caustic = critical_curve - deflections_1d

        caustics.append(caustic)

    return caustics


class TestAbstractPlane(object):
    class TestProperties:
        def test__has_light_profile(self):
            plane = al.plane(galaxies=[al.galaxy(redshift=0.5)], redshift=None)
            assert plane.has_light_profile is False

            plane = al.plane(
                galaxies=[al.galaxy(redshift=0.5, light_profile=al.lp.LightProfile())],
                redshift=None,
            )
            assert plane.has_light_profile is True

            plane = al.plane(
                galaxies=[
                    al.galaxy(redshift=0.5, light_profile=al.lp.LightProfile()),
                    al.galaxy(redshift=0.5),
                ],
                redshift=None,
            )
            assert plane.has_light_profile is True

        def test__has_mass_profile(self):
            plane = al.plane(galaxies=[al.galaxy(redshift=0.5)], redshift=None)
            assert plane.has_mass_profile is False

            plane = al.plane(
                galaxies=[al.galaxy(redshift=0.5, mass_profile=al.mp.MassProfile())],
                redshift=None,
            )
            assert plane.has_mass_profile is True

            plane = al.plane(
                galaxies=[
                    al.galaxy(redshift=0.5, mass_profile=al.mp.MassProfile()),
                    al.galaxy(redshift=0.5),
                ],
                redshift=None,
            )
            assert plane.has_mass_profile is True

        def test__has_pixelization(self):
            plane = al.plane(galaxies=[al.galaxy(redshift=0.5)], redshift=None)
            assert plane.has_pixelization is False

            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Regularization(),
            )

            plane = al.plane(galaxies=[galaxy_pix], redshift=None)
            assert plane.has_pixelization is True

            plane = al.plane(
                galaxies=[galaxy_pix, al.galaxy(redshift=0.5)], redshift=None
            )
            assert plane.has_pixelization is True

        def test__has_regularization(self):
            plane = al.plane(galaxies=[al.galaxy(redshift=0.5)], redshift=None)
            assert plane.has_regularization is False

            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Regularization(),
            )

            plane = al.plane(galaxies=[galaxy_pix], redshift=None)
            assert plane.has_regularization is True

            plane = al.plane(
                galaxies=[galaxy_pix, al.galaxy(redshift=0.5)], redshift=None
            )
            assert plane.has_regularization is True

        def test__has_hyper_galaxy(self):
            plane = al.plane(galaxies=[al.galaxy(redshift=0.5)], redshift=None)
            assert plane.has_hyper_galaxy is False

            galaxy = al.galaxy(redshift=0.5, hyper_galaxy=al.HyperGalaxy())

            plane = al.plane(galaxies=[galaxy], redshift=None)
            assert plane.has_hyper_galaxy is True

            plane = al.plane(galaxies=[galaxy, al.galaxy(redshift=0.5)], redshift=None)
            assert plane.has_hyper_galaxy is True

        def test__hyper_image_of_galaxy_with_pixelization(self):
            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Regularization(),
            )

            plane = al.plane(galaxies=[galaxy_pix], redshift=None)
            assert plane.hyper_galaxy_image_of_galaxy_with_pixelization is None

            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Regularization(),
                hyper_galaxy_image=1,
            )

            plane = al.plane(
                galaxies=[galaxy_pix, al.galaxy(redshift=0.5)], redshift=None
            )
            assert plane.hyper_galaxy_image_of_galaxy_with_pixelization == 1

            plane = al.plane(galaxies=[al.galaxy(redshift=0.5)], redshift=None)

            assert plane.hyper_galaxy_image_of_galaxy_with_pixelization is None

    class TestPixelization:
        def test__no_galaxies_with_pixelizations_in_plane__returns_none(self):
            galaxy_no_pix = al.galaxy(redshift=0.5)

            plane = al.plane(galaxies=[galaxy_no_pix], redshift=None)

            assert plane.pixelization is None

        def test__1_galaxy_in_plane__it_has_pixelization__returns_mapper(self):
            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=1),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )

            plane = al.plane(galaxies=[galaxy_pix], redshift=None)

            assert plane.pixelization.value == 1

            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=2),
                regularization=mock_inversion.MockRegularization(matrix_shape=(2, 2)),
            )
            galaxy_no_pix = al.galaxy(redshift=0.5)

            plane = al.plane(galaxies=[galaxy_no_pix, galaxy_pix], redshift=None)

            assert plane.pixelization.value == 2

        def test__2_galaxies_in_plane__both_have_pixelization__raises_error(self):
            galaxy_pix_0 = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=1),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_pix_1 = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=2),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )

            plane = al.plane(galaxies=[galaxy_pix_0, galaxy_pix_1], redshift=None)

            with pytest.raises(exc.PixelizationException):
                print(plane.pixelization)

    class TestRegularization:
        def test__no_galaxies_with_regularizations_in_plane__returns_none(self):
            galaxy_no_pix = al.galaxy(redshift=0.5)

            plane = al.plane(galaxies=[galaxy_no_pix], redshift=None)

            assert plane.regularization is None

        def test__1_galaxy_in_plane__it_has_regularization__returns_regularization(
            self
        ):
            galaxy_reg = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=1),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )

            plane = al.plane(galaxies=[galaxy_reg], redshift=None)

            assert plane.regularization.shape == (1, 1)

            galaxy_reg = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=1),
                regularization=mock_inversion.MockRegularization(matrix_shape=(2, 2)),
            )
            galaxy_no_reg = al.galaxy(redshift=0.5)

            plane = al.plane(galaxies=[galaxy_no_reg, galaxy_reg], redshift=None)

            assert plane.regularization.shape == (2, 2)

        def test__2_galaxies_in_plane__both_have_regularization__raises_error(self):
            galaxy_reg_0 = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=1),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_reg_1 = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=2),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )

            plane = al.plane(galaxies=[galaxy_reg_0, galaxy_reg_1], redshift=None)

            with pytest.raises(exc.PixelizationException):
                print(plane.regularization)

    class TestMassProfileGeometry:
        def test__extract_centres_of_all_mass_profiles_of_all_galaxies(self):
            g0 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(centre=(1.0, 1.0))
            )
            g1 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(centre=(2.0, 2.0))
            )
            g2 = al.galaxy(
                redshift=0.5,
                mass0=al.mp.SphericalIsothermal(centre=(3.0, 3.0)),
                mass1=al.mp.SphericalIsothermal(centre=(4.0, 4.0)),
            )

            plane = al.plane(galaxies=[al.galaxy(redshift=0.5)], redshift=None)
            assert plane.centres_of_galaxy_mass_profiles == []

            plane = al.plane(galaxies=[g0], redshift=None)
            assert plane.centres_of_galaxy_mass_profiles == [[(1.0, 1.0)]]

            plane = al.plane(galaxies=[g1], redshift=None)
            assert plane.centres_of_galaxy_mass_profiles == [[(2.0, 2.0)]]

            plane = al.plane(galaxies=[g0, g1], redshift=None)
            assert plane.centres_of_galaxy_mass_profiles == [[(1.0, 1.0)], [(2.0, 2.0)]]

            plane = al.plane(galaxies=[g1, g0], redshift=None)
            assert plane.centres_of_galaxy_mass_profiles == [[(2.0, 2.0)], [(1.0, 1.0)]]

            plane = al.plane(
                galaxies=[g0, al.galaxy(redshift=0.5), g1, al.galaxy(redshift=0.5)],
                redshift=None,
            )
            assert plane.centres_of_galaxy_mass_profiles == [[(1.0, 1.0)], [(2.0, 2.0)]]

            plane = al.plane(
                galaxies=[g0, al.galaxy(redshift=0.5), g1, al.galaxy(redshift=0.5), g2],
                redshift=None,
            )
            assert plane.centres_of_galaxy_mass_profiles == [
                [(1.0, 1.0)],
                [(2.0, 2.0)],
                [(3.0, 3.0), (4.0, 4.0)],
            ]

        def test__extracts_axis_ratio_of_all_mass_profiles_of_all_galaxies(self):
            g0 = al.galaxy(
                redshift=0.5, mass=al.mp.EllipticalIsothermal(axis_ratio=0.9)
            )
            g1 = al.galaxy(
                redshift=0.5, mass=al.mp.EllipticalIsothermal(axis_ratio=0.8)
            )
            g2 = al.galaxy(
                redshift=0.5,
                mass0=al.mp.EllipticalIsothermal(axis_ratio=0.7),
                mass1=al.mp.EllipticalIsothermal(axis_ratio=0.6),
            )

            plane = al.plane(galaxies=[al.galaxy(redshift=0.5)], redshift=None)
            assert plane.axis_ratios_of_galaxy_mass_profiles == []

            plane = al.plane(galaxies=[g0], redshift=None)
            assert plane.axis_ratios_of_galaxy_mass_profiles == [[0.9]]

            plane = al.plane(galaxies=[g1], redshift=None)
            assert plane.axis_ratios_of_galaxy_mass_profiles == [[0.8]]

            plane = al.plane(galaxies=[g0, g1], redshift=None)
            assert plane.axis_ratios_of_galaxy_mass_profiles == [[0.9], [0.8]]

            plane = al.plane(galaxies=[g1, g0], redshift=None)
            assert plane.axis_ratios_of_galaxy_mass_profiles == [[0.8], [0.9]]

            plane = al.plane(
                galaxies=[g0, al.galaxy(redshift=0.5), g1, al.galaxy(redshift=0.5)],
                redshift=None,
            )
            assert plane.axis_ratios_of_galaxy_mass_profiles == [[0.9], [0.8]]

            plane = al.plane(
                galaxies=[g0, al.galaxy(redshift=0.5), g1, al.galaxy(redshift=0.5), g2],
                redshift=None,
            )
            assert plane.axis_ratios_of_galaxy_mass_profiles == [
                [0.9],
                [0.8],
                [0.7, 0.6],
            ]

        def test__extracts_phi_of_all_mass_profiles_of_all_galaxies(self):
            g0 = al.galaxy(redshift=0.5, mass=al.mp.EllipticalIsothermal(phi=0.9))
            g1 = al.galaxy(redshift=0.5, mass=al.mp.EllipticalIsothermal(phi=0.8))
            g2 = al.galaxy(
                redshift=0.5,
                mass0=al.mp.EllipticalIsothermal(phi=0.7),
                mass1=al.mp.EllipticalIsothermal(phi=0.6),
            )

            plane = al.plane(galaxies=[al.galaxy(redshift=0.5)], redshift=None)
            assert plane.phis_of_galaxy_mass_profiles == []

            plane = al.plane(galaxies=[g0], redshift=None)
            assert plane.phis_of_galaxy_mass_profiles == [[0.9]]

            plane = al.plane(galaxies=[g1], redshift=None)
            assert plane.phis_of_galaxy_mass_profiles == [[0.8]]

            plane = al.plane(galaxies=[g0, g1], redshift=None)
            assert plane.phis_of_galaxy_mass_profiles == [[0.9], [0.8]]

            plane = al.plane(galaxies=[g1, g0], redshift=None)
            assert plane.phis_of_galaxy_mass_profiles == [[0.8], [0.9]]

            plane = al.plane(
                galaxies=[g0, al.galaxy(redshift=0.5), g1, al.galaxy(redshift=0.5)],
                redshift=None,
            )
            assert plane.phis_of_galaxy_mass_profiles == [[0.9], [0.8]]

            plane = al.plane(
                galaxies=[g0, al.galaxy(redshift=0.5), g1, al.galaxy(redshift=0.5), g2],
                redshift=None,
            )
            assert plane.phis_of_galaxy_mass_profiles == [[0.9], [0.8], [0.7, 0.6]]


class TestAbstractPlaneCosmology(object):
    def test__all_cosmological_quantities_match_cosmology_util(self):
        plane = al.plane(redshift=0.1, cosmology=planck)

        assert (
            plane.arcsec_per_kpc
            == am.util.cosmology.arcsec_per_kpc_from_redshift_and_cosmology(
                redshift=0.1, cosmology=planck
            )
        )

        assert (
            plane.kpc_per_arcsec
            == am.util.cosmology.kpc_per_arcsec_from_redshift_and_cosmology(
                redshift=0.1, cosmology=planck
            )
        )

        assert plane.angular_diameter_distance_to_earth_in_units(
            unit_length="arcsec"
        ) == am.util.cosmology.angular_diameter_distance_to_earth_from_redshift_and_cosmology(
            redshift=0.1, cosmology=planck, unit_length="arcsec"
        )

        plane = al.plane(redshift=0.1, cosmology=planck)

        assert plane.angular_diameter_distance_to_earth_in_units(
            unit_length="kpc"
        ) == am.util.cosmology.angular_diameter_distance_to_earth_from_redshift_and_cosmology(
            redshift=0.1, cosmology=planck, unit_length="kpc"
        )

        plane = al.plane(redshift=1.0, cosmology=planck)

        assert (
            plane.arcsec_per_kpc
            == am.util.cosmology.arcsec_per_kpc_from_redshift_and_cosmology(
                redshift=1.0, cosmology=planck
            )
        )

        assert (
            plane.kpc_per_arcsec
            == am.util.cosmology.kpc_per_arcsec_from_redshift_and_cosmology(
                redshift=1.0, cosmology=planck
            )
        )

        assert plane.angular_diameter_distance_to_earth_in_units(
            unit_length="arcsec"
        ) == am.util.cosmology.angular_diameter_distance_to_earth_from_redshift_and_cosmology(
            redshift=1.0, cosmology=planck, unit_length="arcsec"
        )

        plane = al.plane(redshift=1.0, cosmology=planck)

        assert plane.angular_diameter_distance_to_earth_in_units(
            unit_length="kpc"
        ) == am.util.cosmology.angular_diameter_distance_to_earth_from_redshift_and_cosmology(
            redshift=1.0, cosmology=planck, unit_length="kpc"
        )

        plane = al.plane(redshift=0.6)

        assert plane.cosmic_average_density_in_units(
            unit_length="arcsec", unit_mass="solMass"
        ) == am.util.cosmology.cosmic_average_density_from_redshift_and_cosmology(
            redshift=0.6, cosmology=planck, unit_length="arcsec", unit_mass="solMass"
        )

        plane = al.plane(redshift=0.6, cosmology=planck)

        assert plane.cosmic_average_density_in_units(
            unit_length="kpc", unit_mass="solMass"
        ) == am.util.cosmology.cosmic_average_density_from_redshift_and_cosmology(
            redshift=0.6, cosmology=planck, unit_length="kpc", unit_mass="solMass"
        )


class TestAbstractPlaneLensing(object):
    class TestProfileImage:
        def test__profile_image_from_grid__same_as_its_light_profile_image(
            self, sub_grid_7x7, gal_x1_lp
        ):
            light_profile = gal_x1_lp.light_profiles[0]

            lp_image = light_profile.profile_image_from_grid(grid=sub_grid_7x7)

            # Perform sub gridding average manually
            lp_image_pixel_0 = (
                lp_image[0] + lp_image[1] + lp_image[2] + lp_image[3]
            ) / 4
            lp_image_pixel_1 = (
                lp_image[4] + lp_image[5] + lp_image[6] + lp_image[7]
            ) / 4

            plane = al.plane(galaxies=[gal_x1_lp], redshift=None)

            profile_image = plane.profile_image_from_grid(grid=sub_grid_7x7)

            assert (profile_image.in_1d_binned[0] == lp_image_pixel_0).all()
            assert (profile_image.in_1d_binned[1] == lp_image_pixel_1).all()
            assert (profile_image == lp_image).all()

        def test__profile_image_from_grid__same_as_its_galaxy_image(
            self, sub_grid_7x7, gal_x1_lp
        ):
            galaxy_image = gal_x1_lp.profile_image_from_grid(grid=sub_grid_7x7)

            plane = al.plane(galaxies=[gal_x1_lp], redshift=None)

            profile_image = plane.profile_image_from_grid(grid=sub_grid_7x7)

            assert profile_image == pytest.approx(galaxy_image, 1.0e-4)

        def test__profile_images_of_galaxies(self, sub_grid_7x7):
            # Overwrite one value so intensity in each pixel is different
            sub_grid_7x7[5] = np.array([2.0, 2.0])

            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            lp0 = g0.light_profiles[0]
            lp1 = g1.light_profiles[0]

            lp0_image = lp0.profile_image_from_grid(grid=sub_grid_7x7)
            lp1_image = lp1.profile_image_from_grid(grid=sub_grid_7x7)

            # Perform sub gridding average manually
            lp0_image_pixel_0 = (
                lp0_image[0] + lp0_image[1] + lp0_image[2] + lp0_image[3]
            ) / 4
            lp0_image_pixel_1 = (
                lp0_image[4] + lp0_image[5] + lp0_image[6] + lp0_image[7]
            ) / 4
            lp1_image_pixel_0 = (
                lp1_image[0] + lp1_image[1] + lp1_image[2] + lp1_image[3]
            ) / 4
            lp1_image_pixel_1 = (
                lp1_image[4] + lp1_image[5] + lp1_image[6] + lp1_image[7]
            ) / 4

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            profile_image = plane.profile_image_from_grid(grid=sub_grid_7x7)

            assert profile_image.in_1d_binned[0] == pytest.approx(
                lp0_image_pixel_0 + lp1_image_pixel_0, 1.0e-4
            )
            assert profile_image.in_1d_binned[1] == pytest.approx(
                lp0_image_pixel_1 + lp1_image_pixel_1, 1.0e-4
            )

            profile_image_of_galaxies = plane.profile_images_of_galaxies_from_grid(
                grid=sub_grid_7x7
            )

            assert profile_image_of_galaxies[0].in_1d_binned[0] == lp0_image_pixel_0
            assert profile_image_of_galaxies[0].in_1d_binned[1] == lp0_image_pixel_1
            assert profile_image_of_galaxies[1].in_1d_binned[0] == lp1_image_pixel_0
            assert profile_image_of_galaxies[1].in_1d_binned[1] == lp1_image_pixel_1

        def test__same_as_above__use_multiple_galaxies(self, sub_grid_7x7):
            # Overwrite one value so intensity in each pixel is different
            sub_grid_7x7[5] = np.array([2.0, 2.0])

            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            g0_image = g0.profile_image_from_grid(grid=sub_grid_7x7)

            g1_image = g1.profile_image_from_grid(grid=sub_grid_7x7)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            profile_image = plane.profile_image_from_grid(grid=sub_grid_7x7)

            assert profile_image == pytest.approx(g0_image + g1_image, 1.0e-4)

        def test__plane_has_no_galaxies__image_is_zeros_size_of_unlensed_grid(
            self, sub_grid_7x7
        ):
            plane = al.plane(galaxies=[], redshift=0.5)

            profile_image = plane.profile_image_from_grid(grid=sub_grid_7x7)

            assert profile_image.shape_2d == (7, 7)
            assert (profile_image[0] == 0.0).all()
            assert (profile_image[1] == 0.0).all()

    class TestConvergence:
        def test__convergence_same_as_multiple_galaxies__include_reshape_mapping(
            self, sub_grid_7x7
        ):
            # The *unlensed* sub-grid must be used to compute the convergence. This changes the subgrid to ensure this
            # is the case.

            sub_grid_7x7[5] = np.array([5.0, 2.0])

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    einstein_radius=1.0, centre=(1.0, 0.0)
                ),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    einstein_radius=2.0, centre=(1.0, 1.0)
                ),
            )

            mp0 = g0.mass_profiles[0]
            mp1 = g1.mass_profiles[0]

            mp0_sub_convergence = mp0.convergence_from_grid(grid=sub_grid_7x7)
            mp1_sub_convergence = mp1.convergence_from_grid(grid=sub_grid_7x7)

            mp_sub_convergence = mp0_sub_convergence + mp1_sub_convergence

            # Perform sub gridding average manually

            mp_convergence_pixel_0 = (
                mp_sub_convergence[0]
                + mp_sub_convergence[1]
                + mp_sub_convergence[2]
                + mp_sub_convergence[3]
            ) / 4
            mp_convergence_pixel_1 = (
                mp_sub_convergence[4]
                + mp_sub_convergence[5]
                + mp_sub_convergence[6]
                + mp_sub_convergence[7]
            ) / 4

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            convergence = plane.convergence_from_grid(grid=sub_grid_7x7)

            assert convergence.in_2d_binned[2, 2] == pytest.approx(
                mp_convergence_pixel_0, 1.0e-4
            )
            assert convergence.in_2d_binned[2, 3] == pytest.approx(
                mp_convergence_pixel_1, 1.0e-4
            )

        def test__same_as_above_galaxies___use_galaxy_to_compute_convergence(
            self, sub_grid_7x7
        ):
            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            g0_convergence = g0.convergence_from_grid(grid=sub_grid_7x7)

            g1_convergence = g1.convergence_from_grid(grid=sub_grid_7x7)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            convergence = plane.convergence_from_grid(grid=sub_grid_7x7)

            assert convergence == pytest.approx(g0_convergence + g1_convergence, 1.0e-8)

        def test__plane_has_no_galaxies__convergence_is_zeros_size_of_reshaped_sub_array(
            self, sub_grid_7x7
        ):
            plane = al.plane(galaxies=[], redshift=0.5)

            convergence = plane.convergence_from_grid(grid=sub_grid_7x7)

            assert convergence.sub_shape_1d == sub_grid_7x7.sub_shape_1d

            convergence = plane.convergence_from_grid(grid=sub_grid_7x7)

            assert convergence.sub_shape_2d == (14, 14)

            convergence = plane.convergence_from_grid(grid=sub_grid_7x7)

            assert convergence.shape_2d == (7, 7)

    class TestPotential:
        def test__potential_same_as_multiple_galaxies__include_reshape_mapping(
            self, sub_grid_7x7
        ):
            # The *unlensed* sub-grid must be used to compute the potential. This changes the subgrid to ensure this
            # is the case.

            sub_grid_7x7[5] = np.array([5.0, 2.0])

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    einstein_radius=1.0, centre=(1.0, 0.0)
                ),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    einstein_radius=2.0, centre=(1.0, 1.0)
                ),
            )

            mp0 = g0.mass_profiles[0]
            mp1 = g1.mass_profiles[0]

            mp0_sub_potential = mp0.potential_from_grid(grid=sub_grid_7x7)
            mp1_sub_potential = mp1.potential_from_grid(grid=sub_grid_7x7)

            mp_sub_potential = mp0_sub_potential + mp1_sub_potential

            # Perform sub gridding average manually

            mp_potential_pixel_0 = (
                mp_sub_potential[0]
                + mp_sub_potential[1]
                + mp_sub_potential[2]
                + mp_sub_potential[3]
            ) / 4
            mp_potential_pixel_1 = (
                mp_sub_potential[4]
                + mp_sub_potential[5]
                + mp_sub_potential[6]
                + mp_sub_potential[7]
            ) / 4

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            potential = plane.potential_from_grid(grid=sub_grid_7x7)

            assert potential.in_2d_binned[2, 2] == pytest.approx(
                mp_potential_pixel_0, 1.0e-4
            )
            assert potential.in_2d_binned[2, 3] == pytest.approx(
                mp_potential_pixel_1, 1.0e-4
            )

        def test__same_as_above_galaxies___use_galaxy_to_compute_potential(
            self, sub_grid_7x7
        ):
            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            g0_potential = g0.potential_from_grid(grid=sub_grid_7x7)

            g1_potential = g1.potential_from_grid(grid=sub_grid_7x7)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            potential = plane.potential_from_grid(grid=sub_grid_7x7)

            assert potential == pytest.approx(g0_potential + g1_potential, 1.0e-8)

        def test__plane_has_no_galaxies__potential_is_zeros_size_of_reshaped_sub_array(
            self, sub_grid_7x7
        ):
            plane = al.plane(galaxies=[], redshift=0.5)

            potential = plane.potential_from_grid(grid=sub_grid_7x7)

            assert potential.sub_shape_1d == sub_grid_7x7.sub_shape_1d

            potential = plane.potential_from_grid(grid=sub_grid_7x7)

            assert potential.sub_shape_2d == (14, 14)

            potential = plane.potential_from_grid(grid=sub_grid_7x7)

            assert potential.shape_2d == (7, 7)

    class TestDeflections:
        def test__deflections_from_plane__same_as_the_galaxy_mass_profiles(
            self, sub_grid_7x7
        ):
            # Overwrite one value so intensity in each pixel is different
            sub_grid_7x7[5] = np.array([2.0, 2.0])

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            mp0 = g0.mass_profiles[0]
            mp1 = g1.mass_profiles[0]

            mp0_image = mp0.deflections_from_grid(grid=sub_grid_7x7)
            mp1_image = mp1.deflections_from_grid(grid=sub_grid_7x7)

            # Perform sub gridding average manually
            mp0_image_pixel_0x = (
                mp0_image[0, 0] + mp0_image[1, 0] + mp0_image[2, 0] + mp0_image[3, 0]
            ) / 4
            mp0_image_pixel_1x = (
                mp0_image[4, 0] + mp0_image[5, 0] + mp0_image[6, 0] + mp0_image[7, 0]
            ) / 4
            mp0_image_pixel_0y = (
                mp0_image[0, 1] + mp0_image[1, 1] + mp0_image[2, 1] + mp0_image[3, 1]
            ) / 4
            mp0_image_pixel_1y = (
                mp0_image[4, 1] + mp0_image[5, 1] + mp0_image[6, 1] + mp0_image[7, 1]
            ) / 4

            mp1_image_pixel_0x = (
                mp1_image[0, 0] + mp1_image[1, 0] + mp1_image[2, 0] + mp1_image[3, 0]
            ) / 4
            mp1_image_pixel_1x = (
                mp1_image[4, 0] + mp1_image[5, 0] + mp1_image[6, 0] + mp1_image[7, 0]
            ) / 4
            mp1_image_pixel_0y = (
                mp1_image[0, 1] + mp1_image[1, 1] + mp1_image[2, 1] + mp1_image[3, 1]
            ) / 4
            mp1_image_pixel_1y = (
                mp1_image[4, 1] + mp1_image[5, 1] + mp1_image[6, 1] + mp1_image[7, 1]
            ) / 4

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            deflections = plane.deflections_from_grid(grid=sub_grid_7x7)

            assert deflections.in_1d_binned[0, 0] == pytest.approx(
                mp0_image_pixel_0x + mp1_image_pixel_0x, 1.0e-4
            )
            assert deflections.in_1d_binned[1, 0] == pytest.approx(
                mp0_image_pixel_1x + mp1_image_pixel_1x, 1.0e-4
            )
            assert deflections.in_1d_binned[0, 1] == pytest.approx(
                mp0_image_pixel_0y + mp1_image_pixel_0y, 1.0e-4
            )
            assert deflections.in_1d_binned[1, 1] == pytest.approx(
                mp0_image_pixel_1y + mp1_image_pixel_1y, 1.0e-4
            )

        def test__deflections_same_as_its_galaxy___use_multiple_galaxies(
            self, sub_grid_7x7
        ):
            # Overwrite one value so intensity in each pixel is different
            sub_grid_7x7[5] = np.array([2.0, 2.0])

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            g0_deflections = g0.deflections_from_grid(grid=sub_grid_7x7)

            g1_deflections = g1.deflections_from_grid(grid=sub_grid_7x7)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            deflections = plane.deflections_from_grid(grid=sub_grid_7x7)

            assert deflections == pytest.approx(g0_deflections + g1_deflections, 1.0e-4)

        def test__deflections_numerics__x2_galaxy_in_plane__or_galaxy_x2_sis__deflections_double(
            self, grid_7x7, gal_x1_mp, gal_x2_mp
        ):
            plane = al.plane(galaxies=[gal_x2_mp], redshift=None)

            deflections = plane.deflections_from_grid(grid=grid_7x7)

            assert deflections[0:2] == pytest.approx(
                np.array([[3.0 * 0.707, -3.0 * 0.707], [3.0, 0.0]]), 1e-3
            )

            plane = al.plane(galaxies=[gal_x1_mp, gal_x1_mp], redshift=None)

            deflections = plane.deflections_from_grid(grid=grid_7x7)

            assert deflections[0:2] == pytest.approx(
                np.array([[2.0 * 0.707, -2.0 * 0.707], [2.0, 0.0]]), 1e-3
            )

        def test__plane_has_no_galaxies__deflections_are_zeros_size_of_unlensed_grid(
            self, sub_grid_7x7
        ):
            plane = al.plane(redshift=0.5, galaxies=[])

            deflections = plane.deflections_from_grid(grid=sub_grid_7x7)

            assert deflections.shape_2d == (7, 7)
            assert (deflections.in_1d_binned[0, 0] == 0.0).all()
            assert (deflections.in_1d_binned[0, 1] == 0.0).all()
            assert (deflections.in_1d_binned[1, 0] == 0.0).all()
            assert (deflections.in_1d_binned[0] == 0.0).all()

    class TestDeflectionAnglesviaPotential(object):
        def test__compare_plane_deflections_via_potential_and_calculation(self):
            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            deflections_via_calculation = plane.deflections_from_grid(grid=grid)

            deflections_via_potential = plane.deflections_via_potential_from_grid(
                grid=grid
            )

            mean_error = np.mean(
                deflections_via_potential - deflections_via_calculation
            )

            assert mean_error < 1e-4

        def test__deflections_via_potential_same_as_its_galaxy___use_multiple_galaxies(
            self
        ):
            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            g0_deflections = g0.deflections_via_potential_from_grid(grid=grid)

            g1_deflections = g1.deflections_via_potential_from_grid(grid=grid)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            deflections = plane.deflections_via_potential_from_grid(grid=grid)

            assert deflections == pytest.approx(g0_deflections + g1_deflections, 1.0e-4)

    class TestJacobian(object):
        def test__jacobian_components__two_component_galaxy_plane(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            jacobian = plane.jacobian_from_grid(grid=grid)

            A_12 = jacobian[0][1]
            A_21 = jacobian[1][0]

            mean_error = np.mean(A_12 - A_21)

            assert mean_error < 1e-4

            jacobian = plane.jacobian_from_grid(grid=grid)

            A_12 = jacobian[0][1]
            A_21 = jacobian[1][0]

            mean_error = np.mean(A_12 - A_21)

            assert mean_error < 1e-4

    class TestConvergenceviaJacobian(object):
        def test__compare_plane_convergence_via_jacobian_and_calculation(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            convergence_via_calculation = plane.convergence_from_grid(grid=grid)

            convergence_via_jacobian = plane.convergence_via_jacobian_from_grid(
                grid=grid
            )

            mean_error = np.mean(convergence_via_jacobian - convergence_via_calculation)

            assert mean_error < 1e-1

        def test__convergence_sub_grid_binning_two_component_galaxy_plane(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=2)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            convergence = plane.convergence_via_jacobian_from_grid(grid=grid)

            pixel_first_binned = convergence.in_1d_binned[0]
            pixel_first_binned_manual = (
                convergence[0] + convergence[1] + convergence[2] + convergence[3]
            ) / 4

            assert pixel_first_binned == pytest.approx(pixel_first_binned_manual, 1e-4)

            last_pixel_binned = convergence.in_1d_binned[99]

            last_pixel_binned_manual = (
                convergence[399]
                + convergence[398]
                + convergence[397]
                + convergence[396]
            ) / 4

            assert last_pixel_binned == pytest.approx(last_pixel_binned_manual, 1e-4)

            convergence_via_calculation = plane.convergence_from_grid(grid=grid)

            convergence_via_jacobian = plane.convergence_via_jacobian_from_grid(
                grid=grid
            )

            mean_error = np.mean(convergence_via_jacobian - convergence_via_calculation)

            assert convergence_via_jacobian.in_1d_binned.shape == (400,)
            assert mean_error < 1e-1

        def test__plane_convergence_via_jacobian_same_as_multiple_galaxies(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=2)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            g0_convergence = g0.convergence_via_jacobian_from_grid(grid=grid)

            g1_convergence = g1.convergence_via_jacobian_from_grid(grid=grid)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            convergence = plane.convergence_via_jacobian_from_grid(grid=grid)

            assert convergence == pytest.approx(g0_convergence + g1_convergence, 1.0e-8)

    class TestShearviaJacobian(object):
        def test__shear_sub_grid_binning_two_component_galaxy_plane(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=2)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            shear = plane.shear_via_jacobian_from_grid(grid=grid)

            first_pixel_binned = shear.in_1d_binned[0]
            first_pixel_binned_manual = (shear[0] + shear[1] + shear[2] + shear[3]) / 4

            assert first_pixel_binned == pytest.approx(first_pixel_binned_manual, 1e-4)

            last_pixel_binned = shear.in_1d_binned[99]

            last_pixel_binned_manual = (
                shear[399] + shear[398] + shear[397] + shear[396]
            ) / 4

            assert last_pixel_binned == pytest.approx(last_pixel_binned_manual, 1e-4)

        def test__plane_shear_via_jacobian_same_as_multiple_galaxies(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=2)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            g0_shear = g0.shear_via_jacobian_from_grid(grid=grid)

            g1_shear = g1.shear_via_jacobian_from_grid(grid=grid)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            shear = plane.shear_via_jacobian_from_grid(grid=grid)

            assert shear == pytest.approx(g0_shear + g1_shear, 1.0e-8)

    class TestMagnification(object):
        def test__compare_magnification_from_eigen_values_and_from_determinant__two_component_galaxy_plane(
            self
        ):
            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            magnification_via_determinant = plane.magnification_from_grid(grid=grid)

            tangential_eigen_value = plane.tangential_eigen_value_from_grid(grid=grid)

            radal_eigen_value = plane.radial_eigen_value_from_grid(grid=grid)

            magnification_via_eigen_values = 1 / (
                tangential_eigen_value * radal_eigen_value
            )

            mean_error = np.mean(
                magnification_via_determinant - magnification_via_eigen_values
            )

            assert mean_error < 1e-4

            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=2)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            magnification_via_determinant = plane.magnification_from_grid(grid=grid)

            tangential_eigen_value = plane.tangential_eigen_value_from_grid(grid=grid)

            radal_eigen_value = plane.radial_eigen_value_from_grid(grid=grid)

            magnification_via_eigen_values = 1 / (
                tangential_eigen_value * radal_eigen_value
            )

            mean_error = np.mean(
                magnification_via_determinant - magnification_via_eigen_values
            )

            assert mean_error < 1e-4

        def test__compare_magnification_from_determinant_and_from_convergence_and_shear__two_component_galaxy(
            self
        ):
            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            magnification_via_determinant = plane.magnification_from_grid(grid=grid)

            convergence = plane.convergence_via_jacobian_from_grid(grid=grid)

            shear = plane.shear_via_jacobian_from_grid(grid=grid)

            magnification_via_convergence_and_shear = 1 / (
                (1 - convergence) ** 2 - shear ** 2
            )

            mean_error = np.mean(
                magnification_via_determinant - magnification_via_convergence_and_shear
            )

            assert mean_error < 1e-4

            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=2)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            magnification_via_determinant = plane.magnification_from_grid(grid=grid)

            convergence = plane.convergence_via_jacobian_from_grid(grid=grid)

            shear = plane.shear_via_jacobian_from_grid(grid=grid)

            magnification_via_convergence_and_shear = 1 / (
                (1 - convergence) ** 2 - shear ** 2
            )

            mean_error = np.mean(
                magnification_via_determinant - magnification_via_convergence_and_shear
            )

            assert mean_error < 1e-4

    class TestCriticalCurvesandCaustics(object):
        def test__compare_tangential_critical_curves_from_magnification_and_lamda_t__reg_grid_two_component_galaxy(
            self
        ):
            grid = al.grid.uniform(shape_2d=(100, 100), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.EllipticalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.4, axis_ratio=0.7, phi=40.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            critical_curve_tangential_from_magnification = critical_curve_via_magnification_from_plane_and_grid(
                plane=plane, grid=grid
            )[
                0
            ]

            critical_curve_tangential_from_lambda_t = plane.critical_curves_from_grid(
                grid=grid
            )[0]

            assert critical_curve_tangential_from_lambda_t == pytest.approx(
                critical_curve_tangential_from_magnification, 1e-4
            )

            grid = al.grid.uniform(shape_2d=(100, 100), pixel_scales=0.05, sub_size=2)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            critical_curve_tangential_from_magnification = critical_curve_via_magnification_from_plane_and_grid(
                plane=plane, grid=grid
            )[
                0
            ]

            critical_curve_tangential_from_lambda_t = plane.critical_curves_from_grid(
                grid=grid
            )[0]

            assert critical_curve_tangential_from_lambda_t == pytest.approx(
                critical_curve_tangential_from_magnification, 1e-4
            )

        def test__compare_radial_critical_curves_from_magnification_and_lamda_t__reg_grid_two_component_galaxy(
            self
        ):
            grid = al.grid.uniform(shape_2d=(100, 100), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.EllipticalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.4, axis_ratio=0.7, phi=40.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            critical_curve_radial_from_magnification = critical_curve_via_magnification_from_plane_and_grid(
                plane=plane, grid=grid
            )[
                1
            ]

            critical_curve_radial_from_lambda_t = plane.critical_curves_from_grid(
                grid=grid
            )[1]

            assert sum(critical_curve_radial_from_lambda_t) == pytest.approx(
                sum(critical_curve_radial_from_magnification), 1e-2
            )

            grid = al.grid.uniform(shape_2d=(100, 100), pixel_scales=0.05, sub_size=2)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            critical_curve_radial_from_magnification = critical_curve_via_magnification_from_plane_and_grid(
                plane=plane, grid=grid
            )[
                1
            ]

            critical_curve_radial_from_lambda_t = plane.critical_curves_from_grid(
                grid=grid
            )[1]

            assert sum(critical_curve_radial_from_lambda_t) == pytest.approx(
                sum(critical_curve_radial_from_magnification), 1e-2
            )

        def test__compare_tangential_caustic_from_magnification_and_lambda_t__two_component_galaxy(
            self
        ):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.25, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.EllipticalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.4, axis_ratio=0.7, phi=40.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            caustic_tangential_from_magnification = caustics_via_magnification_from_plane_and_grid(
                plane=plane, grid=grid
            )[
                0
            ]

            caustic_tangential_from_lambda_t = plane.caustics_from_grid(grid=grid)[0]

            assert caustic_tangential_from_lambda_t == pytest.approx(
                caustic_tangential_from_magnification, 5e-1
            )

            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.5, sub_size=2)

            caustic_tangential_from_magnification = caustics_via_magnification_from_plane_and_grid(
                plane=plane, grid=grid
            )[
                0
            ]

            caustic_tangential_from_lambda_t = plane.caustics_from_grid(grid=grid)[0]

            assert caustic_tangential_from_lambda_t == pytest.approx(
                caustic_tangential_from_magnification, 5e-1
            )

        def test__compare_radial_caustic_from_magnification_and_lambda_t__two_component_galaxy(
            self
        ):
            grid = al.grid.uniform(shape_2d=(60, 60), pixel_scales=0.5, sub_size=2)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.EllipticalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.4, axis_ratio=0.7, phi=40.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            caustic_radial_from_magnification = caustics_via_magnification_from_plane_and_grid(
                plane=plane, grid=grid
            )[
                1
            ]

            caustic_radial_from_lambda_t = plane.caustics_from_grid(grid=grid)[1]

            assert sum(caustic_radial_from_lambda_t) == pytest.approx(
                sum(caustic_radial_from_magnification), 1e-2
            )

    class TestLuminosities:
        def test__within_circle_different_luminosity_units__same_as_galaxy_luminosities(
            self
        ):
            g0 = al.galaxy(
                redshift=0.5, luminosity=al.lp.SphericalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, luminosity=al.lp.SphericalSersic(intensity=2.0)
            )

            radius = am.dim.Length(1.0, "arcsec")

            g0_luminosity = g0.luminosity_within_circle_in_units(
                radius=radius, unit_luminosity="eps"
            )
            g1_luminosity = g1.luminosity_within_circle_in_units(
                radius=radius, unit_luminosity="eps"
            )
            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            plane_luminosities = plane.luminosities_of_galaxies_within_circles_in_units(
                radius=radius, unit_luminosity="eps"
            )

            assert plane_luminosities[0] == g0_luminosity
            assert plane_luminosities[1] == g1_luminosity

            g0_luminosity = g0.luminosity_within_circle_in_units(
                radius=radius, unit_luminosity="counts", exposure_time=3.0
            )
            g1_luminosity = g1.luminosity_within_circle_in_units(
                radius=radius, unit_luminosity="counts", exposure_time=3.0
            )
            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            plane_luminosities = plane.luminosities_of_galaxies_within_circles_in_units(
                radius=radius, unit_luminosity="counts", exposure_time=3.0
            )

            assert plane_luminosities[0] == g0_luminosity
            assert plane_luminosities[1] == g1_luminosity

        def test__within_circle_different_distance_units__same_as_galaxy_luminosities(
            self
        ):
            g0 = al.galaxy(
                redshift=0.5, luminosity=al.lp.SphericalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, luminosity=al.lp.SphericalSersic(intensity=2.0)
            )

            radius = am.dim.Length(1.0, "arcsec")

            g0_luminosity = g0.luminosity_within_circle_in_units(radius=radius)
            g1_luminosity = g1.luminosity_within_circle_in_units(radius=radius)

            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            plane_luminosities = plane.luminosities_of_galaxies_within_circles_in_units(
                radius=radius
            )

            assert plane_luminosities[0] == g0_luminosity
            assert plane_luminosities[1] == g1_luminosity

            radius = am.dim.Length(1.0, "kpc")

            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            g0_luminosity = g0.luminosity_within_circle_in_units(radius=radius)
            g1_luminosity = g1.luminosity_within_circle_in_units(radius=radius)

            plane_luminosities = plane.luminosities_of_galaxies_within_circles_in_units(
                radius=radius
            )

            assert plane_luminosities[0] == g0_luminosity
            assert plane_luminosities[1] == g1_luminosity

        def test__within_ellipse_different_luminosity_units__same_as_galaxy_luminosities(
            self
        ):
            g0 = al.galaxy(
                redshift=0.5, luminosity=al.lp.SphericalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, luminosity=al.lp.SphericalSersic(intensity=2.0)
            )

            major_axis = am.dim.Length(1.0, "arcsec")

            g0_luminosity = g0.luminosity_within_ellipse_in_units(
                major_axis=major_axis, unit_luminosity="eps"
            )
            g1_luminosity = g1.luminosity_within_ellipse_in_units(
                major_axis=major_axis, unit_luminosity="eps"
            )
            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            plane_luminosities = plane.luminosities_of_galaxies_within_ellipses_in_units(
                major_axis=major_axis, unit_luminosity="eps"
            )

            assert plane_luminosities[0] == g0_luminosity
            assert plane_luminosities[1] == g1_luminosity

            g0_luminosity = g0.luminosity_within_ellipse_in_units(
                major_axis=major_axis, unit_luminosity="counts", exposure_time=3.0
            )
            g1_luminosity = g1.luminosity_within_ellipse_in_units(
                major_axis=major_axis, unit_luminosity="counts", exposure_time=3.0
            )
            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            plane_luminosities = plane.luminosities_of_galaxies_within_ellipses_in_units(
                major_axis=major_axis, unit_luminosity="counts", exposure_time=3.0
            )

            assert plane_luminosities[0] == g0_luminosity
            assert plane_luminosities[1] == g1_luminosity

        def test__within_ellipse_different_distance_units__same_as_galaxy_luminosities(
            self
        ):
            g0 = al.galaxy(
                redshift=0.5, luminosity=al.lp.SphericalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, luminosity=al.lp.SphericalSersic(intensity=2.0)
            )

            major_axis = am.dim.Length(1.0, "arcsec")

            g0_luminosity = g0.luminosity_within_ellipse_in_units(major_axis=major_axis)
            g1_luminosity = g1.luminosity_within_ellipse_in_units(major_axis=major_axis)
            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            plane_luminosities = plane.luminosities_of_galaxies_within_ellipses_in_units(
                major_axis=major_axis
            )

            assert plane_luminosities[0] == g0_luminosity
            assert plane_luminosities[1] == g1_luminosity

            major_axis = am.dim.Length(1.0, "kpc")

            plane = al.plane(galaxies=[g0, g1], redshift=0.5)

            g0_luminosity = g0.luminosity_within_ellipse_in_units(major_axis=major_axis)
            g1_luminosity = g1.luminosity_within_ellipse_in_units(major_axis=major_axis)

            plane_luminosities = plane.luminosities_of_galaxies_within_ellipses_in_units(
                major_axis=major_axis
            )

            assert plane_luminosities[0] == g0_luminosity
            assert plane_luminosities[1] == g1_luminosity

    class TestMasses:
        def test__within_circle_different_mass_units__same_as_galaxy_masses(self):
            g0 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=2.0)
            )

            radius = am.dim.Length(1.0, "arcsec")

            g0_mass = g0.mass_within_circle_in_units(radius=radius, unit_mass="angular")
            g1_mass = g1.mass_within_circle_in_units(radius=radius, unit_mass="angular")

            plane = al.plane(galaxies=[g0, g1], redshift=0.5)

            plane_masses = plane.masses_of_galaxies_within_circles_in_units(
                radius=radius, unit_mass="angular"
            )

            assert plane_masses[0] == g0_mass
            assert plane_masses[1] == g1_mass

            g0_mass = g0.mass_within_circle_in_units(
                radius=radius, unit_mass="solMass", redshift_source=1.0
            )
            g1_mass = g1.mass_within_circle_in_units(
                radius=radius, unit_mass="solMass", redshift_source=1.0
            )

            plane = al.plane(galaxies=[g0, g1], redshift=0.5)

            plane_masses = plane.masses_of_galaxies_within_circles_in_units(
                radius=radius, unit_mass="solMass", redshift_source=1.0
            )

            assert plane_masses[0] == g0_mass
            assert plane_masses[1] == g1_mass

        def test__within_circle_different_distance_units__same_as_galaxy_masses(self):
            radius = am.dim.Length(1.0, "arcsec")

            g0 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=2.0)
            )

            g0_mass = g0.mass_within_circle_in_units(radius=radius, redshift_source=1.0)
            g1_mass = g1.mass_within_circle_in_units(radius=radius, redshift_source=1.0)

            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            plane_masses = plane.masses_of_galaxies_within_circles_in_units(
                radius=radius, redshift_source=1.0
            )

            assert plane_masses[0] == g0_mass
            assert plane_masses[1] == g1_mass

            radius = am.dim.Length(1.0, "kpc")

            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            g0_mass = g0.mass_within_circle_in_units(
                radius=radius, redshift_source=1.0, kpc_per_arcsec=plane.kpc_per_arcsec
            )
            g1_mass = g1.mass_within_circle_in_units(
                radius=radius, redshift_source=1.0, kpc_per_arcsec=plane.kpc_per_arcsec
            )

            plane_masses = plane.masses_of_galaxies_within_circles_in_units(
                radius=radius, redshift_source=1.0
            )

            assert plane_masses[0] == g0_mass
            assert plane_masses[1] == g1_mass

        def test__within_ellipse_different_mass_units__same_as_galaxy_masses(self):
            g0 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=2.0)
            )

            major_axis = am.dim.Length(1.0, "arcsec")

            g0_mass = g0.mass_within_ellipse_in_units(
                major_axis=major_axis, unit_mass="angular"
            )
            g1_mass = g1.mass_within_ellipse_in_units(
                major_axis=major_axis, unit_mass="angular"
            )
            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            plane_masses = plane.masses_of_galaxies_within_ellipses_in_units(
                major_axis=major_axis, unit_mass="angular"
            )

            assert plane_masses[0] == g0_mass
            assert plane_masses[1] == g1_mass

            g0_mass = g0.mass_within_ellipse_in_units(
                major_axis=major_axis, unit_mass="solMass", redshift_source=1.0
            )
            g1_mass = g1.mass_within_ellipse_in_units(
                major_axis=major_axis, unit_mass="solMass", redshift_source=1.0
            )

            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            plane_masses = plane.masses_of_galaxies_within_ellipses_in_units(
                major_axis=major_axis, unit_mass="solMass", redshift_source=1.0
            )

            assert plane_masses[0] == g0_mass
            assert plane_masses[1] == g1_mass

        def test__within_ellipse_different_distance_units__same_as_galaxy_masses(self):
            g0 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=2.0)
            )

            major_axis = am.dim.Length(1.0, "arcsec")

            g0_mass = g0.mass_within_ellipse_in_units(
                major_axis=major_axis, redshift_source=1.0
            )
            g1_mass = g1.mass_within_ellipse_in_units(
                major_axis=major_axis, redshift_source=1.0
            )
            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            plane_masses = plane.masses_of_galaxies_within_ellipses_in_units(
                major_axis=major_axis, redshift_source=1.0
            )

            assert plane_masses[0] == g0_mass
            assert plane_masses[1] == g1_mass

            major_axis = am.dim.Length(1.0, "kpc")

            plane = al.plane(galaxies=[g0, g1], redshift=0.5)
            g0_mass = g0.mass_within_ellipse_in_units(
                major_axis=major_axis,
                redshift_source=1.0,
                kpc_per_arcsec=plane.kpc_per_arcsec,
            )
            g1_mass = g1.mass_within_ellipse_in_units(
                major_axis=major_axis,
                redshift_source=1.0,
                kpc_per_arcsec=plane.kpc_per_arcsec,
            )
            plane_masses = plane.masses_of_galaxies_within_ellipses_in_units(
                major_axis=major_axis, redshift_source=1.0
            )

            assert plane_masses[0] == g0_mass
            assert plane_masses[1] == g1_mass

    class TestEinsteinRadiiAndMass:
        def test__plane_has_galaxies_with_sis_profiles__einstein_radius_and_mass_sum_of_sis_profiles(
            self
        ):
            cosmology = MockCosmology(
                arcsec_per_kpc=0.5, kpc_per_arcsec=2.0, critical_surface_density=2.0
            )

            sis_0 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=1.0)
            )
            sis_1 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=2.0)
            )

            plane = al.plane(galaxies=[sis_0], redshift=0.5, cosmology=cosmology)

            assert plane.einstein_radius_in_units(
                unit_length="arcsec"
            ) == pytest.approx(1.0, 1.0e-4)
            assert plane.einstein_radius_in_units(unit_length="kpc") == pytest.approx(
                2.0, 1.0e-4
            )
            assert plane.einstein_mass_in_units(unit_mass="angular") == pytest.approx(
                np.pi, 1.0e-4
            )
            assert plane.einstein_mass_in_units(
                unit_mass="solMass", redshift_source=1.0
            ) == pytest.approx(2.0 * np.pi, 1.0e-4)

            plane = al.plane(galaxies=[sis_1], redshift=0.5, cosmology=cosmology)

            assert plane.einstein_radius_in_units(
                unit_length="arcsec"
            ) == pytest.approx(2.0, 1.0e-4)
            assert plane.einstein_radius_in_units(unit_length="kpc") == pytest.approx(
                4.0, 1.0e-4
            )
            assert plane.einstein_mass_in_units(unit_mass="angular") == pytest.approx(
                np.pi * 2.0 ** 2.0, 1.0e-4
            )
            assert plane.einstein_mass_in_units(
                unit_mass="solMass", redshift_source=1.0
            ) == pytest.approx(2.0 * np.pi * 2.0 ** 2.0, 1.0e-4)

            plane = al.plane(galaxies=[sis_0, sis_1], redshift=0.5, cosmology=cosmology)

            assert plane.einstein_radius_in_units(
                unit_length="arcsec"
            ) == pytest.approx(3.0, 1.0e-4)
            assert plane.einstein_radius_in_units(unit_length="kpc") == pytest.approx(
                2.0 * 3.0, 1.0e-4
            )
            assert plane.einstein_mass_in_units(unit_mass="angular") == pytest.approx(
                np.pi * (1.0 + 2.0 ** 2.0), 1.0e-4
            )
            assert plane.einstein_mass_in_units(
                unit_mass="solMass", redshift_source=1.0
            ) == pytest.approx(2.0 * np.pi * (1.0 + 2.0 ** 2.0), 1.0e-4)

        def test__include_galaxy_with_no_mass_profile__does_not_impact_einstein_radius_or_mass(
            self
        ):
            sis_0 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=1.0)
            )
            sis_1 = al.galaxy(
                redshift=0.5, mass=al.mp.SphericalIsothermal(einstein_radius=2.0)
            )
            g0 = al.galaxy(redshift=0.5)

            plane = al.plane(galaxies=[sis_0, g0], redshift=0.5)

            assert plane.einstein_radius_in_units(
                unit_length="arcsec"
            ) == pytest.approx(1.0, 1.0e-4)
            assert plane.einstein_mass_in_units(unit_mass="angular") == pytest.approx(
                np.pi, 1.0e-4
            )

            plane = al.plane(galaxies=[sis_1, g0], redshift=0.5)

            assert plane.einstein_radius_in_units(
                unit_length="arcsec"
            ) == pytest.approx(2.0, 1.0e-4)
            assert plane.einstein_mass_in_units(unit_mass="angular") == pytest.approx(
                np.pi * 2.0 ** 2.0, 1.0e-4
            )

            plane = al.plane(galaxies=[sis_0, sis_1, g0], redshift=0.5)

            assert plane.einstein_radius_in_units(
                unit_length="arcsec"
            ) == pytest.approx(3.0, 1.0e-4)
            assert plane.einstein_mass_in_units(unit_mass="angular") == pytest.approx(
                np.pi * (1.0 + 2.0 ** 2.0), 1.0e-4
            )

        def test__only_galaxies_without_mass_profiles__einstein_radius_and_mass_are_none(
            self
        ):
            g0 = al.galaxy(redshift=0.5)

            plane = al.plane(galaxies=[g0], redshift=0.5)

            assert plane.einstein_radius_in_units() is None
            assert plane.einstein_mass_in_units() is None

            plane = al.plane(galaxies=[g0, g0], redshift=0.5)

            assert plane.einstein_radius_in_units() is None
            assert plane.einstein_mass_in_units() is None


class TestAbstractPlaneData(object):
    class TestBlurredImagePlaneImage:
        def test__blurred_image_from_grid_and_psf(
            self, sub_grid_7x7, blurring_grid_7x7, psf_3x3, convolver_7x7
        ):

            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            blurred_g0_image = g0.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                blurring_grid=blurring_grid_7x7,
                convolver=convolver_7x7,
            )

            blurred_g1_image = g1.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                blurring_grid=blurring_grid_7x7,
                convolver=convolver_7x7,
            )

            plane = al.plane(redshift=0.5, galaxies=[g0, g1])

            blurred_image = plane.blurred_profile_image_from_grid_and_psf(
                grid=sub_grid_7x7, blurring_grid=blurring_grid_7x7, psf=psf_3x3
            )

            assert blurred_image.in_1d == pytest.approx(
                blurred_g0_image.in_1d + blurred_g1_image.in_1d, 1.0e-4
            )

            assert blurred_image.in_2d == pytest.approx(
                blurred_g0_image.in_2d + blurred_g1_image.in_2d, 1.0e-4
            )

        def test__blurred_image_of_galaxies_from_grid_and_psf(
            self, sub_grid_7x7, blurring_grid_7x7, psf_3x3
        ):
            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            blurred_g0_image = g0.blurred_profile_image_from_grid_and_psf(
                grid=sub_grid_7x7, blurring_grid=blurring_grid_7x7, psf=psf_3x3
            )

            blurred_g1_image = g1.blurred_profile_image_from_grid_and_psf(
                grid=sub_grid_7x7, blurring_grid=blurring_grid_7x7, psf=psf_3x3
            )

            plane = al.plane(redshift=0.5, galaxies=[g0, g1])

            blurred_images_of_galaxies = plane.blurred_profile_images_of_galaxies_from_grid_and_psf(
                grid=sub_grid_7x7, blurring_grid=blurring_grid_7x7, psf=psf_3x3
            )

            assert blurred_g0_image.shape_1d == 9
            assert blurred_images_of_galaxies[0].in_1d == pytest.approx(
                blurred_g0_image.in_1d, 1.0e-4
            )
            assert blurred_g1_image.shape_1d == 9
            assert blurred_images_of_galaxies[1].in_1d == pytest.approx(
                blurred_g1_image.in_1d, 1.0e-4
            )

            assert blurred_images_of_galaxies[0].in_2d == pytest.approx(
                blurred_g0_image.in_2d, 1.0e-4
            )
            assert blurred_images_of_galaxies[1].in_2d == pytest.approx(
                blurred_g1_image.in_2d, 1.0e-4
            )

        def test__blurred_image_from_grid_and_convolver(
            self, sub_grid_7x7, blurring_grid_7x7, convolver_7x7
        ):
            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            blurred_g0_image = g0.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            blurred_g1_image = g1.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            plane = al.plane(redshift=0.5, galaxies=[g0, g1])

            blurred_image = plane.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            assert blurred_image.in_1d == pytest.approx(
                blurred_g0_image.in_1d + blurred_g1_image.in_1d, 1.0e-4
            )

            assert blurred_image.in_2d == pytest.approx(
                blurred_g0_image.in_2d + blurred_g1_image.in_2d, 1.0e-4
            )

        def test__blurred_image_of_galaxies_from_grid_and_convolver(
            self, sub_grid_7x7, blurring_grid_7x7, convolver_7x7
        ):
            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            blurred_g0_image = g0.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            blurred_g1_image = g1.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            plane = al.plane(redshift=0.5, galaxies=[g0, g1])

            blurred_images_of_galaxies = plane.blurred_profile_images_of_galaxies_from_grid_and_convolver(
                grid=sub_grid_7x7,
                blurring_grid=blurring_grid_7x7,
                convolver=convolver_7x7,
            )

            assert blurred_g0_image.shape_1d == 9
            assert blurred_images_of_galaxies[0].in_1d == pytest.approx(
                blurred_g0_image.in_1d, 1.0e-4
            )
            assert blurred_g1_image.shape_1d == 9
            assert blurred_images_of_galaxies[1].in_1d == pytest.approx(
                blurred_g1_image.in_1d, 1.0e-4
            )

            assert blurred_images_of_galaxies[0].in_2d == pytest.approx(
                blurred_g0_image.in_2d, 1.0e-4
            )
            assert blurred_images_of_galaxies[1].in_2d == pytest.approx(
                blurred_g1_image.in_2d, 1.0e-4
            )

    class TestVisibilities:
        def test__visibilities_from_grid_and_transformer(
            self, sub_grid_7x7, transformer_7x7_7
        ):
            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )

            image = g0.profile_image_from_grid(grid=sub_grid_7x7)

            visibilities = transformer_7x7_7.visibilities_from_image(image=image)

            plane = al.plane(redshift=0.5, galaxies=[g0])

            plane_visibilities = plane.profile_visibilities_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            assert (visibilities == plane_visibilities).all()

            g1 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            image = g0.profile_image_from_grid(
                grid=sub_grid_7x7
            ) + g1.profile_image_from_grid(grid=sub_grid_7x7)

            visibilities = transformer_7x7_7.visibilities_from_image(image=image)

            plane = al.plane(redshift=0.5, galaxies=[g0, g1])

            plane_visibilities = plane.profile_visibilities_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            assert visibilities == pytest.approx(plane_visibilities, 1.0e-4)

        def test__visibilities_from_grid_and_transformer__plane_has_no_galaxies__returns_zeros(
            self, sub_grid_7x7, transformer_7x7_7
        ):
            plane = al.plane(redshift=0.5, galaxies=[])

            plane_visibilities = plane.profile_visibilities_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            assert (plane_visibilities.in_1d == np.zeros((7, 2))).all()

        def test__visibilities_of_galaxies_from_grid_and_transformer(
            self, sub_grid_7x7, transformer_7x7_7
        ):
            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )

            g1 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            g0_image = g0.profile_image_from_grid(grid=sub_grid_7x7)

            g1_image = g1.profile_image_from_grid(grid=sub_grid_7x7)

            g0_visibilities = transformer_7x7_7.visibilities_from_image(image=g0_image)

            g1_visibilities = transformer_7x7_7.visibilities_from_image(image=g1_image)

            plane = al.plane(redshift=0.5, galaxies=[g0, g1])

            plane_visibilities_of_galaxies = plane.profile_visibilities_of_galaxies_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            assert (g0_visibilities == plane_visibilities_of_galaxies[0]).all()
            assert (g1_visibilities == plane_visibilities_of_galaxies[1]).all()

            plane_visibilities = plane.profile_visibilities_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            assert sum(plane_visibilities_of_galaxies) == pytest.approx(
                plane_visibilities, 1.0e-4
            )

    class TestGridIrregular:
        def test__no_galaxies_with_pixelizations_in_plane__returns_none(
            self, sub_grid_7x7
        ):
            galaxy_no_pix = al.galaxy(redshift=0.5)

            plane = al.plane(galaxies=[galaxy_no_pix], redshift=0.5)

            sparse_grid = plane.sparse_image_plane_grid_from_grid(grid=sub_grid_7x7)

            assert sparse_grid is None

        def test__1_galaxy_in_plane__it_has_pixelization__returns_sparse_grid(
            self, sub_grid_7x7
        ):
            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(
                    value=1, grid=np.array([[1.0, 1.0]])
                ),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )

            plane = al.plane(galaxies=[galaxy_pix], redshift=0.5)

            sparse_grid = plane.sparse_image_plane_grid_from_grid(grid=sub_grid_7x7)

            assert (sparse_grid == np.array([[1.0, 1.0]])).all()

        def test__1_galaxy_in_plane__it_has_pixelization_and_hyper_image_returns_sparse_grid_and_uses_hyper_image(
            self, sub_grid_7x7
        ):
            # In the MockPixelization class the grid is returned if hyper image=None, and grid*hyper image is
            # returned otherwise.

            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(
                    value=1, grid=np.array([[1.0, 1.0]])
                ),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
                hyper_galaxy_image=2,
            )

            plane = al.plane(galaxies=[galaxy_pix], redshift=0.5)

            sparse_grid = plane.sparse_image_plane_grid_from_grid(grid=sub_grid_7x7)

            assert (sparse_grid == np.array([[2.0, 2.0]])).all()

    class TestMapper:
        def test__no_galaxies_with_pixelizations_in_plane__returns_none(
            self, sub_grid_7x7
        ):
            galaxy_no_pix = al.galaxy(redshift=0.5)

            plane = al.plane(galaxies=[galaxy_no_pix], redshift=0.5)

            mapper = plane.mapper_from_grid_and_sparse_grid(
                grid=sub_grid_7x7, sparse_grid=sub_grid_7x7
            )

            assert mapper is None

        def test__1_galaxy_in_plane__it_has_pixelization__returns_mapper(
            self, sub_grid_7x7
        ):
            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=1),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )

            plane = al.plane(galaxies=[galaxy_pix], redshift=0.5)

            mapper = plane.mapper_from_grid_and_sparse_grid(
                grid=sub_grid_7x7, sparse_grid=sub_grid_7x7
            )

            assert mapper == 1

            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=1),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_no_pix = al.galaxy(redshift=0.5)

            plane = al.plane(galaxies=[galaxy_no_pix, galaxy_pix], redshift=0.5)

            mapper = plane.mapper_from_grid_and_sparse_grid(
                grid=sub_grid_7x7, sparse_grid=sub_grid_7x7
            )

            assert mapper == 1

        def test__inversion_uses_border_is_false__still_returns_mapper(
            self, sub_grid_7x7
        ):
            galaxy_pix = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=1),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_no_pix = al.galaxy(redshift=0.5)

            plane = al.plane(galaxies=[galaxy_no_pix, galaxy_pix], redshift=0.5)

            mapper = plane.mapper_from_grid_and_sparse_grid(
                grid=sub_grid_7x7,
                sparse_grid=sub_grid_7x7,
                inversion_uses_border=False,
            )

            assert mapper == 1

        def test__2_galaxies_in_plane__both_have_pixelization__raises_error(
            self, sub_grid_7x7
        ):
            galaxy_pix_0 = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=1),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_pix_1 = al.galaxy(
                redshift=0.5,
                pixelization=mock_inversion.MockPixelization(value=2),
                regularization=mock_inversion.MockRegularization(matrix_shape=(1, 1)),
            )

            plane = al.plane(galaxies=[galaxy_pix_0, galaxy_pix_1], redshift=None)

            with pytest.raises(exc.PixelizationException):
                plane.mapper_from_grid_and_sparse_grid(
                    grid=sub_grid_7x7,
                    sparse_grid=sub_grid_7x7,
                    inversion_uses_border=False,
                )

    class TestPlaneImage:
        def test__3x3_grid__extracts_max_min_coordinates__ignores_other_coordinates_more_central(
            self, sub_grid_7x7
        ):
            sub_grid_7x7[1] = np.array([2.0, 2.0])

            galaxy = al.galaxy(
                redshift=0.5, light=al.lp.EllipticalSersic(intensity=1.0)
            )

            plane = al.plane(galaxies=[galaxy], redshift=None)

            plane_image_from_func = al.util.lens.plane_image_of_galaxies_from_grid(
                shape=(7, 7),
                grid=sub_grid_7x7.geometry.unmasked_grid,
                galaxies=[galaxy],
            )

            plane_image_from_plane = plane.plane_image_from_grid(grid=sub_grid_7x7)

            assert (plane_image_from_func.array == plane_image_from_plane.array).all()

        def test__ensure_index_of_plane_image_has_negative_arcseconds_at_start(self,):
            # The grid coordinates -2.0 -> 2.0 mean a plane of shape (5,5) has arc second coordinates running over
            # -1.6, -0.8, 0.0, 0.8, 1.6. The origin -1.6, -1.6 of the model_galaxy means its brighest pixel should be
            # index 0 of the 1D grid and (0,0) of the 2d plane datas_.

            mask = al.mask.unmasked(shape_2d=(5, 5), pixel_scales=1.0, sub_size=1)

            grid = al.masked.grid.from_mask(mask=mask)

            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(centre=(1.6, -1.6), intensity=1.0),
            )
            plane = al.plane(galaxies=[g0], redshift=None)

            plane_image = plane.plane_image_from_grid(grid=grid)

            assert plane_image.array.shape_2d == (5, 5)
            assert np.unravel_index(
                plane_image.array.in_2d.argmax(), plane_image.array.in_2d.shape
            ) == (0, 0)

            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(centre=(1.6, 1.6), intensity=1.0),
            )
            plane = al.plane(galaxies=[g0], redshift=None)

            plane_image = plane.plane_image_from_grid(grid=grid)

            assert np.unravel_index(
                plane_image.array.in_2d.argmax(), plane_image.array.in_2d.shape
            ) == (0, 4)

            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(
                    centre=(-1.6, -1.6), intensity=1.0
                ),
            )
            plane = al.plane(galaxies=[g0], redshift=None)

            plane_image = plane.plane_image_from_grid(grid=grid)

            assert np.unravel_index(
                plane_image.array.in_2d.argmax(), plane_image.array.in_2d.shape
            ) == (4, 0)

            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(centre=(-1.6, 1.6), intensity=1.0),
            )
            plane = al.plane(galaxies=[g0], redshift=None)

            plane_image = plane.plane_image_from_grid(grid=grid)

            assert np.unravel_index(
                plane_image.array.in_2d.argmax(), plane_image.array.in_2d.shape
            ) == (4, 4)

    class TestContributionMaps:
        def test__x2_hyper_galaxy__use_numerical_values_for_noise_scaling(self):
            hyper_galaxy_0 = al.HyperGalaxy(
                contribution_factor=0.0, noise_factor=0.0, noise_power=1.0
            )
            hyper_galaxy_1 = al.HyperGalaxy(
                contribution_factor=1.0, noise_factor=0.0, noise_power=1.0
            )

            hyper_model_image = al.array.manual_2d(array=[[0.5, 1.0, 1.5]])

            hyper_galaxy_image_0 = al.array.manual_2d(array=[[0.5, 1.0, 1.5]])
            hyper_galaxy_image_1 = al.array.manual_2d(array=[[0.5, 1.0, 1.5]])

            galaxy_0 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_0,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image_0,
            )

            galaxy_1 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_1,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image_1,
            )

            plane = al.plane(redshift=0.5, galaxies=[galaxy_0, galaxy_1])

            assert (
                plane.contribution_maps_of_galaxies[0].in_2d
                == np.array([[1.0, 1.0, 1.0]])
            ).all()
            assert (
                plane.contribution_maps_of_galaxies[1].in_2d
                == np.array([[5.0 / 9.0, (1.0 / 2.0) / (1.5 / 2.5), 1.0]])
            ).all()

        def test__contribution_maps_are_same_as_hyper_galaxy_calculation(self):
            hyper_model_image = al.array.manual_2d([[2.0, 4.0, 10.0]])
            hyper_galaxy_image = al.array.manual_2d([[1.0, 5.0, 8.0]])

            hyper_galaxy_0 = al.HyperGalaxy(contribution_factor=5.0)
            hyper_galaxy_1 = al.HyperGalaxy(contribution_factor=10.0)

            contribution_map_0 = hyper_galaxy_0.contribution_map_from_hyper_images(
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            contribution_map_1 = hyper_galaxy_1.contribution_map_from_hyper_images(
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            galaxy_0 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_0,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            galaxy_1 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_1,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            plane = al.plane(redshift=0.5, galaxies=[galaxy_0])

            assert (
                plane.contribution_maps_of_galaxies[0].in_1d == contribution_map_0
            ).all()

            plane = al.plane(redshift=0.5, galaxies=[galaxy_1])

            assert (
                plane.contribution_maps_of_galaxies[0].in_1d == contribution_map_1
            ).all()

            plane = al.plane(redshift=0.5, galaxies=[galaxy_1, galaxy_0])

            assert (
                plane.contribution_maps_of_galaxies[0].in_1d == contribution_map_1
            ).all()
            assert (
                plane.contribution_maps_of_galaxies[1].in_1d == contribution_map_0
            ).all()

        def test__contriution_maps_are_none_for_galaxy_without_hyper_galaxy(self):
            hyper_model_image = al.array.manual_2d([[2.0, 4.0, 10.0]])
            hyper_galaxy_image = al.array.manual_2d([[1.0, 5.0, 8.0]])

            hyper_galaxy = al.HyperGalaxy(contribution_factor=5.0)

            contribution_map = hyper_galaxy.contribution_map_from_hyper_images(
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            galaxy = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            plane = al.plane(
                redshift=0.5,
                galaxies=[galaxy, al.galaxy(redshift=0.5), al.galaxy(redshift=0.5)],
            )

            assert (
                plane.contribution_maps_of_galaxies[0].in_1d == contribution_map
            ).all()
            assert plane.contribution_maps_of_galaxies[1] == None
            assert plane.contribution_maps_of_galaxies[2] == None

    class TestHyperNoiseMap:
        def test__x2_hyper_galaxy__use_numerical_values_of_hyper_noise_map_scaling(
            self
        ):
            noise_map = al.array.manual_2d([[1.0, 2.0, 3.0]])

            hyper_galaxy_0 = al.HyperGalaxy(
                contribution_factor=0.0, noise_factor=1.0, noise_power=1.0
            )
            hyper_galaxy_1 = al.HyperGalaxy(
                contribution_factor=3.0, noise_factor=1.0, noise_power=2.0
            )

            hyper_model_image = al.array.manual_2d([[0.5, 1.0, 1.5]])

            hyper_galaxy_image_0 = al.array.manual_2d([[0.0, 1.0, 1.5]])
            hyper_galaxy_image_1 = al.array.manual_2d([[1.0, 1.0, 1.5]])

            galaxy_0 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_0,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image_0,
            )

            galaxy_1 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_1,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image_1,
            )

            plane = al.plane(redshift=0.5, galaxies=[galaxy_0, galaxy_1])

            hyper_noise_maps = plane.hyper_noise_maps_of_galaxies_from_noise_map(
                noise_map=noise_map
            )

            assert (hyper_noise_maps[0].in_1d == np.array([0.0, 2.0, 3.0])).all()
            assert hyper_noise_maps[1].in_1d == pytest.approx(
                np.array([0.73468, (2.0 * 0.75) ** 2.0, 3.0 ** 2.0]), 1.0e-4
            )

        def test__hyper_noise_maps_are_same_as_hyper_galaxy_calculation(self):
            noise_map = al.array.manual_2d([[5.0, 3.0, 1.0]])

            hyper_model_image = al.array.manual_2d([[2.0, 4.0, 10.0]])
            hyper_galaxy_image = al.array.manual_2d([[1.0, 5.0, 8.0]])

            hyper_galaxy_0 = al.HyperGalaxy(contribution_factor=5.0)
            hyper_galaxy_1 = al.HyperGalaxy(contribution_factor=10.0)

            contribution_map_0 = hyper_galaxy_0.contribution_map_from_hyper_images(
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            contribution_map_1 = hyper_galaxy_1.contribution_map_from_hyper_images(
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            hyper_noise_map_0 = hyper_galaxy_0.hyper_noise_map_from_contribution_map(
                noise_map=noise_map, contribution_map=contribution_map_0
            )

            hyper_noise_map_1 = hyper_galaxy_1.hyper_noise_map_from_contribution_map(
                noise_map=noise_map, contribution_map=contribution_map_1
            )

            galaxy_0 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_0,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            galaxy_1 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_1,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            plane = al.plane(redshift=0.5, galaxies=[galaxy_0])

            hyper_noise_maps = plane.hyper_noise_maps_of_galaxies_from_noise_map(
                noise_map=noise_map
            )
            assert (hyper_noise_maps[0].in_1d == hyper_noise_map_0).all()

            plane = al.plane(redshift=0.5, galaxies=[galaxy_1])

            hyper_noise_maps = plane.hyper_noise_maps_of_galaxies_from_noise_map(
                noise_map=noise_map
            )
            assert (hyper_noise_maps[0].in_1d == hyper_noise_map_1).all()

            plane = al.plane(redshift=0.5, galaxies=[galaxy_1, galaxy_0])

            hyper_noise_maps = plane.hyper_noise_maps_of_galaxies_from_noise_map(
                noise_map=noise_map
            )
            assert (hyper_noise_maps[0].in_1d == hyper_noise_map_1).all()
            assert (hyper_noise_maps[1].in_1d == hyper_noise_map_0).all()

        def test__hyper_noise_maps_are_none_for_galaxy_without_hyper_galaxy(self):
            noise_map = al.array.manual_2d([[5.0, 3.0, 1.0]])

            hyper_model_image = al.array.manual_2d([[2.0, 4.0, 10.0]])
            hyper_galaxy_image = al.array.manual_2d([[1.0, 5.0, 8.0]])

            hyper_galaxy_0 = al.HyperGalaxy(contribution_factor=5.0)
            hyper_galaxy_1 = al.HyperGalaxy(contribution_factor=10.0)

            contribution_map_0 = hyper_galaxy_0.contribution_map_from_hyper_images(
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            contribution_map_1 = hyper_galaxy_1.contribution_map_from_hyper_images(
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            hyper_noise_map_0 = hyper_galaxy_0.hyper_noise_map_from_contribution_map(
                noise_map=noise_map, contribution_map=contribution_map_0
            )

            hyper_noise_map_1 = hyper_galaxy_1.hyper_noise_map_from_contribution_map(
                noise_map=noise_map, contribution_map=contribution_map_1
            )

            galaxy_0 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_0,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            galaxy_1 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_1,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            plane = al.plane(redshift=0.5, galaxies=[galaxy_0, al.galaxy(redshift=0.5)])

            hyper_noise_maps = plane.hyper_noise_maps_of_galaxies_from_noise_map(
                noise_map=noise_map
            )
            assert (hyper_noise_maps[0].in_1d == hyper_noise_map_0).all()
            assert hyper_noise_maps[1].in_1d == np.zeros(shape=(3, 1))

            plane = al.plane(redshift=0.5, galaxies=[al.galaxy(redshift=0.5), galaxy_1])

            hyper_noise_maps = plane.hyper_noise_maps_of_galaxies_from_noise_map(
                noise_map=noise_map
            )
            assert hyper_noise_maps[0].in_1d == np.zeros(shape=(3, 1))
            assert (hyper_noise_maps[1].in_1d == hyper_noise_map_1).all()

            plane = al.plane(
                redshift=0.5,
                galaxies=[
                    al.galaxy(redshift=0.5),
                    galaxy_1,
                    galaxy_0,
                    al.galaxy(redshift=0.5),
                ],
            )

            hyper_noise_maps = plane.hyper_noise_maps_of_galaxies_from_noise_map(
                noise_map=noise_map
            )
            assert hyper_noise_maps[0].in_1d == np.zeros(shape=(3, 1))
            assert (hyper_noise_maps[1].in_1d == hyper_noise_map_1).all()
            assert (hyper_noise_maps[2].in_1d == hyper_noise_map_0).all()
            assert hyper_noise_maps[3].in_1d == np.zeros(shape=(3, 1))

        def test__hyper_noise_map_from_noise_map__is_sum_of_galaxy_hyper_noise_maps__filters_nones(
            self
        ):
            noise_map = al.array.manual_2d([[5.0, 3.0, 1.0]])

            hyper_model_image = al.array.manual_2d([[2.0, 4.0, 10.0]])
            hyper_galaxy_image = al.array.manual_2d([[1.0, 5.0, 8.0]])

            hyper_galaxy_0 = al.HyperGalaxy(contribution_factor=5.0)
            hyper_galaxy_1 = al.HyperGalaxy(contribution_factor=10.0)

            contribution_map_0 = hyper_galaxy_0.contribution_map_from_hyper_images(
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            contribution_map_1 = hyper_galaxy_1.contribution_map_from_hyper_images(
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            hyper_noise_map_0 = hyper_galaxy_0.hyper_noise_map_from_contribution_map(
                noise_map=noise_map, contribution_map=contribution_map_0
            )

            hyper_noise_map_1 = hyper_galaxy_1.hyper_noise_map_from_contribution_map(
                noise_map=noise_map, contribution_map=contribution_map_1
            )

            galaxy_0 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_0,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            galaxy_1 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_1,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
            )

            plane = al.plane(redshift=0.5, galaxies=[galaxy_0])

            hyper_noise_map = plane.hyper_noise_map_from_noise_map(noise_map=noise_map)
            assert (hyper_noise_map.in_1d == hyper_noise_map_0).all()

            plane = al.plane(redshift=0.5, galaxies=[galaxy_1])

            hyper_noise_map = plane.hyper_noise_map_from_noise_map(noise_map=noise_map)
            assert (hyper_noise_map.in_1d == hyper_noise_map_1).all()

            plane = al.plane(redshift=0.5, galaxies=[galaxy_1, galaxy_0])

            hyper_noise_map = plane.hyper_noise_map_from_noise_map(noise_map=noise_map)
            assert (
                hyper_noise_map.in_1d == hyper_noise_map_0 + hyper_noise_map_1
            ).all()

            plane = al.plane(
                redshift=0.5,
                galaxies=[
                    al.galaxy(redshift=0.5),
                    galaxy_1,
                    galaxy_0,
                    al.galaxy(redshift=0.5),
                ],
            )

            hyper_noise_map = plane.hyper_noise_map_from_noise_map(noise_map=noise_map)
            assert (
                hyper_noise_map.in_1d == hyper_noise_map_0 + hyper_noise_map_1
            ).all()

        def test__plane_has_no_hyper_galaxies__hyper_noise_map_function_returns_none(
            self
        ):
            noise_map = al.array.manual_2d([[5.0, 3.0, 1.0]])

            plane = al.plane(redshift=0.5, galaxies=[al.galaxy(redshift=0.5)])
            hyper_noise_map = plane.hyper_noise_map_from_noise_map(noise_map=noise_map)

            assert hyper_noise_map == np.zeros((3, 1))


class TestPlane(object):
    class TestTracedGrid:
        def test__traced_grid_same_as_manual_deflections_calc_via_galaxy___use_multiple_galaxies(
            self, sub_grid_7x7
        ):
            # Overwrite one value so intensity in each pixel is different
            sub_grid_7x7[5] = np.array([2.0, 2.0])

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            g0_deflections = g0.deflections_from_grid(grid=sub_grid_7x7)

            g1_deflections = g1.deflections_from_grid(grid=sub_grid_7x7)

            traced_grid = sub_grid_7x7 - (g0_deflections + g1_deflections)

            plane = al.plane(galaxies=[g0, g1], redshift=None)

            plane_traced_grid = plane.traced_grid_from_grid(grid=sub_grid_7x7)

            assert plane_traced_grid == pytest.approx(traced_grid, 1.0e-4)

        def test__traced_grid_numerics__uses_deflections__x2_sis_galaxies(
            self, sub_grid_7x7_simple, gal_x1_mp
        ):
            plane = al.plane(galaxies=[gal_x1_mp, gal_x1_mp], redshift=None)

            traced_grid = plane.traced_grid_from_grid(grid=sub_grid_7x7_simple)

            assert traced_grid[0] == pytest.approx(
                np.array([1.0 - 2.0 * 0.707, 1.0 - 2.0 * 0.707]), 1e-3
            )
            assert traced_grid[1] == pytest.approx(np.array([-1.0, 0.0]), 1e-3)
            assert traced_grid[2] == pytest.approx(
                np.array([1.0 - 2.0 * 0.707, 1.0 - 2.0 * 0.707]), 1e-3
            )
            assert traced_grid[3] == pytest.approx(np.array([-1.0, 0.0]), 1e-3)

        def test__plane_has_no_galaxies__traced_grid_is_input_grid_of_sub_grid_7x7(
            self, sub_grid_7x7
        ):
            plane = al.plane(galaxies=[], redshift=1.0)

            traced_grid = plane.traced_grid_from_grid(grid=sub_grid_7x7)

            assert (traced_grid == sub_grid_7x7).all()

    class TestGalaxies:
        def test__no_galaxies__raises_exception_if_no_plane_redshift_input(self):
            plane = al.plane(galaxies=[], redshift=0.5)
            assert plane.redshift == 0.5

            with pytest.raises(exc.RayTracingException):
                al.plane(galaxies=[])

        def test__galaxy_redshifts_gives_list_of_redshifts(self):
            g0 = al.galaxy(redshift=1.0)
            g1 = al.galaxy(redshift=1.0)
            g2 = al.galaxy(redshift=1.0)

            plane = al.plane(galaxies=[g0, g1, g2])

            assert plane.redshift == 1.0
            assert plane.galaxy_redshifts == [1.0, 1.0, 1.0]

        def test__galaxies_have_different_redshifts__exception_is_raised_if_redshift_not_input(
            self
        ):
            g0 = al.galaxy(redshift=0.1)
            g1 = al.galaxy(redshift=1.0)

            with pytest.raises(exc.RayTracingException):
                al.plane(galaxies=[g0, g1])

            g0 = al.galaxy(redshift=0.4)
            g1 = al.galaxy(redshift=0.5)
            g2 = al.galaxy(redshift=0.6)

            plane = al.plane(galaxies=[g0, g1, g2], redshift=0.5)

            assert plane.redshift == 0.5

    class TestSummarize:
        def test__plane_x2_galaxies__summarize_is_correct(self):
            sersic_0 = al.lp.SphericalSersic(
                intensity=1.0, effective_radius=2.0, sersic_index=2.0
            )
            sersic_1 = al.lp.SphericalSersic(
                intensity=2.0, effective_radius=2.0, sersic_index=2.0
            )

            sis_0 = al.mp.SphericalIsothermal(einstein_radius=1.0)
            sis_1 = al.mp.SphericalIsothermal(einstein_radius=2.0)

            g0 = al.galaxy(
                redshift=0.5,
                light_profile_0=sersic_0,
                light_profile_1=sersic_1,
                mass_profile_0=sis_0,
                mass_profile_1=sis_1,
            )

            g1 = al.galaxy(redshift=0.6, light_profile_0=sersic_0, mass_profile_0=sis_0)

            plane = al.plane(galaxies=[g0, g1], redshift=0.6)

            summary_text = plane.summarize_in_units(
                radii=[am.dim.Length(10.0), am.dim.Length(500.0)],
                whitespace=50,
                unit_length="arcsec",
                unit_luminosity="eps",
                unit_mass="angular",
            )

            i = 0
            assert summary_text[i] == "Plane\n"
            i += 1
            assert (
                summary_text[i]
                == "redshift                                          0.60"
            )
            i += 1
            assert (
                summary_text[i]
                == "kpc_per_arcsec                                    6.88"
            )
            i += 1
            assert (
                summary_text[i]
                == "angular_diameter_distance_to_earth                206264.81"
            )
            i += 1
            assert summary_text[i] == "\n"
            i += 1
            assert summary_text[i] == "Galaxy\n"
            i += 1
            assert (
                summary_text[i]
                == "redshift                                          0.50"
            )
            i += 1
            assert summary_text[i] == "\nGALAXY LIGHT\n\n"
            i += 1
            assert (
                summary_text[i]
                == "luminosity_within_10.00_arcsec                    1.8854e+02 eps"
            )
            i += 1
            assert (
                summary_text[i]
                == "luminosity_within_500.00_arcsec                   1.9573e+02 eps"
            )
            i += 1
            assert summary_text[i] == "\nLIGHT PROFILES:\n\n"
            i += 1
            assert summary_text[i] == "Light Profile = SphericalSersic\n"
            i += 1
            assert (
                summary_text[i]
                == "luminosity_within_10.00_arcsec                    6.2848e+01 eps"
            )
            i += 1
            assert (
                summary_text[i]
                == "luminosity_within_500.00_arcsec                   6.5243e+01 eps"
            )
            i += 1
            assert summary_text[i] == "\n"
            i += 1
            assert summary_text[i] == "Light Profile = SphericalSersic\n"
            i += 1
            assert (
                summary_text[i]
                == "luminosity_within_10.00_arcsec                    1.2570e+02 eps"
            )
            i += 1
            assert (
                summary_text[i]
                == "luminosity_within_500.00_arcsec                   1.3049e+02 eps"
            )
            i += 1
            assert summary_text[i] == "\n"
            i += 1
            assert summary_text[i] == "\nGALAXY MASS\n\n"
            i += 1
            assert (
                summary_text[i]
                == "einstein_radius                                   3.00 arcsec"
            )
            i += 1
            assert (
                summary_text[i]
                == "einstein_mass                                     1.5708e+01 angular"
            )
            i += 1
            assert (
                summary_text[i]
                == "mass_within_10.00_arcsec                          9.4248e+01 angular"
            )
            i += 1
            assert (
                summary_text[i]
                == "mass_within_500.00_arcsec                         4.7124e+03 angular"
            )
            i += 1
            assert summary_text[i] == "\nMASS PROFILES:\n\n"
            i += 1
            assert summary_text[i] == "Mass Profile = SphericalIsothermal\n"
            i += 1
            assert (
                summary_text[i]
                == "einstein_radius                                   1.00 arcsec"
            )
            i += 1
            assert (
                summary_text[i]
                == "einstein_mass                                     3.1416e+00 angular"
            )
            i += 1
            assert (
                summary_text[i]
                == "mass_within_10.00_arcsec                          3.1416e+01 angular"
            )
            i += 1
            assert (
                summary_text[i]
                == "mass_within_500.00_arcsec                         1.5708e+03 angular"
            )
            i += 1
            assert summary_text[i] == "\n"
            i += 1
            assert summary_text[i] == "Mass Profile = SphericalIsothermal\n"
            i += 1
            assert (
                summary_text[i]
                == "einstein_radius                                   2.00 arcsec"
            )
            i += 1
            assert (
                summary_text[i]
                == "einstein_mass                                     1.2566e+01 angular"
            )
            i += 1
            assert (
                summary_text[i]
                == "mass_within_10.00_arcsec                          6.2832e+01 angular"
            )
            i += 1
            assert (
                summary_text[i]
                == "mass_within_500.00_arcsec                         3.1416e+03 angular"
            )
            i += 1
            assert summary_text[i] == "\n"
            i += 1
            assert summary_text[i] == "\n"
            i += 1
            assert summary_text[i] == "Galaxy\n"
            i += 1
            assert (
                summary_text[i]
                == "redshift                                          0.60"
            )
            i += 1
            assert summary_text[i] == "\nGALAXY LIGHT\n\n"
            i += 1
            assert (
                summary_text[i]
                == "luminosity_within_10.00_arcsec                    6.2848e+01 eps"
            )
            i += 1
            assert (
                summary_text[i]
                == "luminosity_within_500.00_arcsec                   6.5243e+01 eps"
            )
            i += 1
            assert summary_text[i] == "\nLIGHT PROFILES:\n\n"
            i += 1
            assert summary_text[i] == "Light Profile = SphericalSersic\n"
            i += 1
            assert (
                summary_text[i]
                == "luminosity_within_10.00_arcsec                    6.2848e+01 eps"
            )
            i += 1
            assert (
                summary_text[i]
                == "luminosity_within_500.00_arcsec                   6.5243e+01 eps"
            )
            i += 1
            assert summary_text[i] == "\n"
            i += 1
            assert summary_text[i] == "\nGALAXY MASS\n\n"
            i += 1
            assert (
                summary_text[i]
                == "einstein_radius                                   1.00 arcsec"
            )
            i += 1
            assert (
                summary_text[i]
                == "einstein_mass                                     3.1416e+00 angular"
            )
            i += 1
            assert (
                summary_text[i]
                == "mass_within_10.00_arcsec                          3.1416e+01 angular"
            )
            i += 1
            assert (
                summary_text[i]
                == "mass_within_500.00_arcsec                         1.5708e+03 angular"
            )
            i += 1
            assert summary_text[i] == "\nMASS PROFILES:\n\n"
            i += 1
            assert summary_text[i] == "Mass Profile = SphericalIsothermal\n"
            i += 1
            assert (
                summary_text[i]
                == "einstein_radius                                   1.00 arcsec"
            )
            i += 1
            assert (
                summary_text[i]
                == "einstein_mass                                     3.1416e+00 angular"
            )
            i += 1
            assert (
                summary_text[i]
                == "mass_within_10.00_arcsec                          3.1416e+01 angular"
            )
            i += 1
            assert (
                summary_text[i]
                == "mass_within_500.00_arcsec                         1.5708e+03 angular"
            )
            i += 1
            assert summary_text[i] == "\n"
            i += 1


class TestPlaneImage:
    def test__compute_xticks_from_grid_correctly(self):

        array = al.array.ones(shape_2d=(3, 3), pixel_scales=(5.0, 1.0))

        plane_image = plane.PlaneImage(array=array, grid=None)
        assert plane_image.xticks == pytest.approx(
            np.array([-1.5, -0.5, 0.5, 1.5]), 1e-3
        )

        array = al.array.ones(shape_2d=(3, 3), pixel_scales=(5.0, 0.5))

        plane_image = plane.PlaneImage(array=array, grid=None)
        assert plane_image.xticks == pytest.approx(
            np.array([-0.75, -0.25, 0.25, 0.75]), 1e-3
        )

        array = al.array.ones(shape_2d=(1, 6), pixel_scales=(5.0, 1.0))

        plane_image = plane.PlaneImage(array=array, grid=None)
        assert plane_image.xticks == pytest.approx(
            np.array([-3.0, -1.0, 1.0, 3.0]), 1e-2
        )

    def test__compute_yticks_from_grid_correctly(self):

        array = al.array.ones(shape_2d=(3, 3), pixel_scales=(1.0, 5.0))

        plane_image = plane.PlaneImage(array=array, grid=None)
        assert plane_image.yticks == pytest.approx(
            np.array([-1.5, -0.5, 0.5, 1.5]), 1e-3
        )

        array = al.array.ones(shape_2d=(3, 3), pixel_scales=(0.5, 5.0))

        plane_image = plane.PlaneImage(array=array, grid=None)
        assert plane_image.yticks == pytest.approx(
            np.array([-0.75, -0.25, 0.25, 0.75]), 1e-3
        )

        array = al.array.ones(shape_2d=(6, 1), pixel_scales=(1.0, 5.0))

        plane_image = plane.PlaneImage(array=array, grid=None)
        assert plane_image.yticks == pytest.approx(
            np.array([-3.0, -1.0, 1.0, 3.0]), 1e-2
        )
