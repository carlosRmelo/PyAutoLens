import autofit as af
import autolens as al
from test_autolens.integration.tests.imaging import runner

test_type = "reult_passing"
test_name = "source_choice_parametric_via_phase"
data_name = "lens_sie__source_smooth"
instrument = "vro"


def source_with_previous_model_or_instance(phase):
    """Setup the source source model using the previous pipeline or phase results.

    This function is required because the source light model is not specified by the pipeline itself (e.g. the previous
    pipelines determines if the source was modeled using parametric light profiles or an inversion.

    If the source was parametric this function returns the source as a model, given that a parametric source should be
    fitted for simultaneously with the mass model.

    If the source was an inversion then it is returned as an instance, given that the inversion parameters do not need
    to be fitted for alongside the mass model.

    The bool include_hyper_source determines if the hyper-galaxy used to scale the sources noises is included in the
    model fitting.
    """

    if phase.result.model.galaxies.source.pixelization is None:

        return al.GalaxyModel(
            redshift=phase.result.instance.galaxies.source.redshift,
            sersic=phase.result.model.galaxies.source.sersic,
        )

    else:

        return al.GalaxyModel(
            redshift=phase.result.instance.galaxies.source.redshift,
            pixelization=phase.result.instance.galaxies.source.pixelization,
            regularization=phase.result.instance.galaxies.source.regularization,
        )


def make_pipeline(name, folders, search=af.DynestyStatic()):

    phase1 = al.PhaseImaging(
        phase_name="phase_1",
        folders=folders,
        galaxies=dict(
            lens=al.GalaxyModel(redshift=0.5, mass=al.mp.EllipticalIsothermal),
            source=al.GalaxyModel(redshift=1.0, sersic=al.lp.EllipticalSersic),
        ),
        sub_size=1,
        search=search,
    )

    phase1.search.const_efficiency_mode = True
    phase1.search.n_live_points = 20
    phase1.search.facc = 0.8

    # We want to set up the source from the result, where:

    # If it is parametric, it is a model (thus N = 12).
    # If it is an inversion, it is an instance (Thus N = 5)

    # When we use a phase.result, this doesn't work, cause the pixelization is a promise. We also cannot use hasattr,
    # because even a parametric source has a pixelization (it is None).

    source = source_with_previous_model_or_instance(phase=phase1)

    phase2 = al.PhaseImaging(
        phase_name="phase_2",
        folders=folders,
        galaxies=dict(lens=phase1.result.model.galaxies.lens, source=source),
        sub_size=1,
        search=search,
    )

    return al.PipelineDataset(name, phase1, phase2)


if __name__ == "__main__":
    import sys

    runner.run(sys.modules[__name__])
