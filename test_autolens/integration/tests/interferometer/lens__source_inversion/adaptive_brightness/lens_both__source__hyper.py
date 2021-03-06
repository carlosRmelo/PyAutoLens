import autofit as af
import autolens as al
from test_autolens.integration.tests.interferometer import runner

test_type = "lens__source_inversion"
test_name = "lens_both__source_adaptive_brightness__hyper"
data_name = "lens_light__source_smooth"
instrument = "sma"


def make_pipeline(name, folders, real_space_mask, search=af.DynestyStatic()):

    phase1 = al.PhaseInterferometer(
        phase_name="phase_1",
        folders=folders,
        galaxies=dict(
            lens=al.GalaxyModel(
                redshift=0.5,
                light=al.lp.EllipticalSersic,
                mass=al.mp.EllipticalIsothermal,
            ),
            source=al.GalaxyModel(redshift=1.0, light=al.lp.EllipticalSersic),
        ),
        real_space_mask=real_space_mask,
        search=search,
    )

    class InversionPhase(al.PhaseInterferometer):
        def customize_priors(self, results):

            ## Lens Mass, SIE -> SIE, Shear -> Shear ###

            self.galaxies.lens.light = results.from_phase(
                "phase_1"
            ).instance.galaxies.lens.light
            self.galaxies.lens.mass = results.from_phase(
                "phase_1"
            ).instance.galaxies.lens.mass

    phase2 = InversionPhase(
        phase_name="phase_2_weighted_regularization",
        folders=folders,
        galaxies=dict(
            lens=al.GalaxyModel(
                redshift=0.5,
                light=al.lp.EllipticalSersic,
                mass=al.mp.EllipticalIsothermal,
                shear=al.mp.ExternalShear,
            ),
            source=al.GalaxyModel(
                redshift=1.0,
                pixelization=al.pix.VoronoiBrightnessImage,
                regularization=al.reg.AdaptiveBrightness,
            ),
        ),
        real_space_mask=real_space_mask,
        search=search,
    )

    phase2.search.const_efficiency_mode = True
    phase2.search.n_live_points = 40
    phase2.search.facc = 0.8

    phase2 = phase2.extend_with_multiple_hyper_phases(
        hyper_galaxies_search=True, include_inversion=True
    )

    class InversionPhase(al.PhaseInterferometer):
        def customize_priors(self, results):

            ## Lens Mass, SIE -> SIE, Shear -> Shear ###

            self.galaxies.lens = results.from_phase("phase_1").model.galaxies.lens

            self.galaxies.source.pixelization = (
                results.last.inversion.instance.galaxies.source.pixelization
            )
            self.galaxies.source.regularization = (
                results.last.inversion.instance.galaxies.source.regularization
            )

    phase3 = InversionPhase(
        phase_name="phase_3",
        folders=folders,
        galaxies=dict(
            lens=al.GalaxyModel(
                redshift=0.5,
                light=al.lp.EllipticalSersic,
                mass=al.mp.EllipticalIsothermal,
                shear=al.mp.ExternalShear,
            ),
            source=al.GalaxyModel(
                redshift=1.0,
                pixelization=al.pix.VoronoiBrightnessImage,
                regularization=al.reg.AdaptiveBrightness,
            ),
        ),
        real_space_mask=real_space_mask,
        search=search,
    )

    phase3.search.const_efficiency_mode = True
    phase3.search.n_live_points = 40
    phase3.search.facc = 0.8

    phase3 = phase3.extend_with_multiple_hyper_phases(
        hyper_galaxies_search=True, include_inversion=True
    )

    return al.PipelineDataset(name, phase1, phase2, phase3)


if __name__ == "__main__":
    import sys

    runner.run(sys.modules[__name__])
