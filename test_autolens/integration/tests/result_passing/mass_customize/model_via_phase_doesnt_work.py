import autofit as af
import autolens as al
from test_autolens.integration.tests.imaging import runner

test_type = "reult_passing"
test_name = "mass_customize_model_via_phase_doesnt_work"
data_label = "lens_sie__source_smooth"
instrument = "vro"


def make_pipeline(name, phase_folders, non_linear_class=af.MultiNest):

    # For this mass model, we fix the centre, making N = 10.

    mass = af.PriorModel(al.mp.EllipticalIsothermal)
    mass.centre.centre_0 = 0.0
    mass.centre.centre_1 = 0.0

    phase1 = al.PhaseImaging(
        phase_name="phase_1",
        phase_folders=phase_folders,
        galaxies=dict(
            lens=al.GalaxyModel(redshift=0.5, mass=mass),
            source=al.GalaxyModel(redshift=1.0, light=al.lp.EllipticalSersic),
        ),
        sub_size=1,
        non_linear_class=non_linear_class,
    )

    phase1.search.const_efficiency_mode = True
    phase1.search.n_live_points = 60
    phase1.search.sampling_efficiency = 0.8

    # We now want to create a lens galaxy whose mass model centres are free parameters, increaisng N to 12.

    # It doesn't work - N stays at 10 and the centres do not take on the priors specified.

    lens = phase1.result.model.galaxies.lens
    lens.mass.centre.centre_0 = af.GaussianPrior(mean=0.0, sigma=0.05)
    lens.mass.centre.centre_1 = af.GaussianPrior(mean=0.0, sigma=0.05)

    phase2 = al.PhaseImaging(
        phase_name="phase_2",
        phase_folders=phase_folders,
        galaxies=dict(lens=lens, source=phase1.result.model.galaxies.source),
        sub_size=1,
        non_linear_class=non_linear_class,
    )

    return al.PipelineDataset(name, phase1, phase2)


if __name__ == "__main__":
    import sys

    runner.run(sys.modules[__name__])
