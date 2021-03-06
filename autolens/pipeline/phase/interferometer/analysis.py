import autofit as af
from autoarray.exc import InversionException
from autofit.exc import FitException
from autogalaxy.galaxy import galaxy as g
from autogalaxy.pipeline.phase.dataset import analysis as ag_analysis
from autolens.fit import fit
from autolens.pipeline import visualizer
from autolens.pipeline.phase.dataset import analysis as analysis_dataset


class Analysis(ag_analysis.Analysis, analysis_dataset.Analysis):
    def __init__(
        self,
        masked_interferometer,
        settings,
        cosmology,
        image_path=None,
        results=None,
        log_likelihood_cap=None,
    ):

        super(Analysis, self).__init__(
            settings=settings,
            cosmology=cosmology,
            results=results,
            log_likelihood_cap=log_likelihood_cap,
        )

        self.visualizer = visualizer.PhaseInterferometerVisualizer(
            masked_dataset=masked_interferometer, image_path=image_path
        )

        self.visualizer.visualize_hyper_images(
            hyper_galaxy_image_path_dict=self.hyper_galaxy_image_path_dict,
            hyper_model_image=self.hyper_model_image,
        )

        self.masked_dataset = masked_interferometer

        result = ag_analysis.last_result_with_use_as_hyper_dataset(results=results)

        if result is not None:

            self.hyper_galaxy_visibilities_path_dict = (
                result.hyper_galaxy_visibilities_path_dict
            )

            self.hyper_model_visibilities = result.hyper_model_visibilities

        else:

            self.hyper_galaxy_visibilities_path_dict = None
            self.hyper_model_visibilities = None

    @property
    def masked_interferometer(self):
        return self.masked_dataset

    def log_likelihood_function(self, instance):
        """
        Determine the fit of a lens galaxy and source galaxy to the masked_interferometer in this lens.

        Parameters
        ----------
        instance
            A model instance with attributes

        Returns
        -------
        fit : Fit
            A fractional value indicating how well this model fit and the model masked_interferometer itself
        """

        self.associate_hyper_images(instance=instance)
        tracer = self.tracer_for_instance(instance=instance)

        self.settings.settings_lens.check_positions_trace_within_threshold_via_tracer(
            tracer=tracer, positions=self.masked_dataset.positions
        )

        hyper_background_noise = self.hyper_background_noise_for_instance(
            instance=instance
        )

        try:
            fit = self.masked_interferometer_fit_for_tracer(
                tracer=tracer, hyper_background_noise=hyper_background_noise
            )
            return fit.figure_of_merit
        except InversionException as e:
            raise FitException from e

    def associate_hyper_visibilities(
        self, instance: af.ModelInstance
    ) -> af.ModelInstance:
        """
        Takes visibilities from the last result, if there is one, and associates them with galaxies in this phase
        where full-path galaxy names match.

        If the galaxy collection has a different name then an association is not made.

        e.g.
        galaxies.lens will match with:
            galaxies.lens
        but not with:
            galaxies.lens
            galaxies.source

        Parameters
        ----------
        instance
            A model instance with 0 or more galaxies in its tree

        Returns
        -------
        instance
           The input instance with visibilities associated with galaxies where possible.
        """
        if self.hyper_galaxy_visibilities_path_dict is not None:
            for galaxy_path, galaxy in instance.path_instance_tuples_for_class(
                g.Galaxy
            ):
                if galaxy_path in self.hyper_galaxy_visibilities_path_dict:
                    galaxy.hyper_model_visibilities = self.hyper_model_visibilities
                    galaxy.hyper_galaxy_visibilities = self.hyper_galaxy_visibilities_path_dict[
                        galaxy_path
                    ]

        return instance

    def masked_interferometer_fit_for_tracer(self, tracer, hyper_background_noise):

        return fit.FitInterferometer(
            masked_interferometer=self.masked_dataset,
            tracer=tracer,
            hyper_background_noise=hyper_background_noise,
            settings_pixelization=self.settings.settings_pixelization,
            settings_inversion=self.settings.settings_inversion,
        )

    def visualize(self, instance, during_analysis):

        self.associate_hyper_images(instance=instance)
        tracer = self.tracer_for_instance(instance=instance)
        hyper_background_noise = self.hyper_background_noise_for_instance(
            instance=instance
        )

        fit = self.masked_interferometer_fit_for_tracer(
            tracer=tracer, hyper_background_noise=hyper_background_noise
        )

        if tracer.has_mass_profile:

            try:

                visualizer = self.visualizer.new_visualizer_with_preloaded_critical_curves_and_caustics(
                    preloaded_critical_curves=tracer.critical_curves,
                    preloaded_caustics=tracer.caustics,
                )

            except Exception or IndexError or ValueError:

                visualizer = self.visualizer

        else:

            visualizer = self.visualizer

        visualizer.visualize_ray_tracing(
            tracer=fit.tracer, during_analysis=during_analysis
        )
        visualizer.visualize_fit(fit=fit, during_analysis=during_analysis)
