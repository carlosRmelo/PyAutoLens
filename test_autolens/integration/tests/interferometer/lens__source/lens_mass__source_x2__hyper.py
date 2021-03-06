import autofit as af
import autolens as al
from test_autolens.integration.tests.interferometer import runner

test_type = "lens__source"
test_name = "lens_mass__source_x2__hyper"
data_name = "lens_sie__source_smooth"
instrument = "sma"


def make_pipeline(name, folders, real_space_mask, search=af.DynestyStatic()):

    phase1 = al.PhaseInterferometer(
        phase_name="phase_1",
        folders=folders,
        galaxies=dict(
            lens=al.GalaxyModel(redshift=0.5, mass=al.mp.EllipticalIsothermal),
            source_0=al.GalaxyModel(redshift=1.0, light=al.lp.EllipticalSersic),
        ),
        real_space_mask=real_space_mask,
        search=search,
    )

    phase1.search.const_efficiency_mode = True
    phase1.search.n_live_points = 60
    phase1.search.facc = 0.7

    phase2 = al.PhaseInterferometer(
        phase_name="phase_2",
        folders=folders,
        galaxies=dict(
            lens=al.GalaxyModel(
                redshift=0.5, mass=phase1.result.model.galaxies.lens.mass
            ),
            source_0=al.GalaxyModel(
                redshift=1.0, light=phase1.result.model.galaxies.source_0.light
            ),
            source_1=al.GalaxyModel(redshift=1.0, light=al.lp.EllipticalSersic),
        ),
        real_space_mask=real_space_mask,
        search=search,
    )

    phase2.search.const_efficiency_mode = True
    phase2.search.n_live_points = 60
    phase2.search.facc = 0.7

    phase2 = phase2.extend_with_multiple_hyper_phases(hyper_galaxies_search=True)

    class HyperLensSourcePlanePhase(al.PhaseInterferometer):
        def customize_priors(self, results):

            self.galaxies.source_0.hyper_galaxy = (
                results.last.hyper_combined.instance.galaxies.source_0.hyper_galaxy
            )

            self.galaxies.source_1.hyper_galaxy = (
                results.last.hyper_combined.instance.galaxies.source_1.hyper_galaxy
            )

    phase3 = HyperLensSourcePlanePhase(
        phase_name="phase_3",
        folders=folders,
        galaxies=dict(
            lens=al.GalaxyModel(
                redshift=0.5, mass=phase2.result.model.galaxies.lens.mass
            ),
            source_0=al.GalaxyModel(
                redshift=1.0,
                light=phase2.result.model.galaxies.source_0.light,
                hyper_galaxy=phase2.result.hyper_combined.instance.galaxies.source_0.hyper_galaxy,
            ),
            source_1=al.GalaxyModel(
                redshift=1.0,
                light=phase2.result.model.galaxies.source_1.light,
                hyper_galaxy=phase2.result.hyper_combined.instance.galaxies.source_1.hyper_galaxy,
            ),
        ),
        real_space_mask=real_space_mask,
        search=search,
    )

    phase3.search.const_efficiency_mode = True
    phase3.search.n_live_points = 40
    phase3.search.facc = 0.8

    return al.PipelineDataset(name, phase1, phase2, phase3)


if __name__ == "__main__":
    import sys

    runner.run(sys.modules[__name__])
