from autoconf import conf
from autoarray.inversion import pixelizations as pix
from autoarray.exc import InversionException, GridException
from autofit.exc import FitException
from autogalaxy.pipeline.phase.dataset import analysis as ag_analysis
from autolens.fit import fit
from autolens.pipeline import visualizer
from autolens.pipeline.phase.dataset import analysis as analysis_dataset

import copy


class Analysis(ag_analysis.Analysis, analysis_dataset.Analysis):
    def __init__(
        self,
        masked_imaging,
        settings,
        cosmology,
        image_path=None,
        results=None,
        log_likelihood_cap=None,
    ):

        super().__init__(
            settings=settings,
            cosmology=cosmology,
            results=results,
            log_likelihood_cap=log_likelihood_cap,
        )

        self.visualizer = visualizer.PhaseImagingVisualizer(
            masked_dataset=masked_imaging, image_path=image_path, results=results
        )

        self.visualizer.visualize_hyper_images(
            hyper_galaxy_image_path_dict=self.hyper_galaxy_image_path_dict,
            hyper_model_image=self.hyper_model_image,
        )

        self.masked_dataset = masked_imaging

    @property
    def masked_imaging(self):
        return self.masked_dataset

    def log_likelihood_function(self, instance):
        """
        Determine the fit of a lens galaxy and source galaxy to the masked_imaging in this lens.

        Parameters
        ----------
        instance
            A model instance with attributes

        Returns
        -------
        fit : Fit
            A fractional value indicating how well this model fit and the model masked_imaging itself
        """

        self.associate_hyper_images(instance=instance)
        tracer = self.tracer_for_instance(instance=instance)

        self.settings.settings_lens.check_positions_trace_within_threshold_via_tracer(
            tracer=tracer, positions=self.masked_dataset.positions
        )

        hyper_image_sky = self.hyper_image_sky_for_instance(instance=instance)

        hyper_background_noise = self.hyper_background_noise_for_instance(
            instance=instance
        )

        try:
            fit = self.masked_imaging_fit_for_tracer(
                tracer=tracer,
                hyper_image_sky=hyper_image_sky,
                hyper_background_noise=hyper_background_noise,
            )

            return fit.figure_of_merit
        except (InversionException or GridException or OverflowError) as e:
            raise FitException from e

    def masked_imaging_fit_for_tracer(
        self, tracer, hyper_image_sky, hyper_background_noise
    ):

        return fit.FitImaging(
            masked_imaging=self.masked_dataset,
            tracer=tracer,
            hyper_image_sky=hyper_image_sky,
            hyper_background_noise=hyper_background_noise,
            settings_pixelization=self.settings.settings_pixelization,
            settings_inversion=self.settings.settings_inversion,
        )

    def stochastic_log_evidences_for_instance(
        self, instance, histogram_samples=100, histogram_bins=10
    ):

        instance = self.associate_hyper_images(instance=instance)
        tracer = self.tracer_for_instance(instance=instance)

        if not tracer.has_pixelization:
            return None

        if not isinstance(
            tracer.pixelizations_of_planes[-1], pix.VoronoiBrightnessImage
        ):
            return None

        hyper_image_sky = self.hyper_image_sky_for_instance(instance=instance)

        hyper_background_noise = self.hyper_background_noise_for_instance(
            instance=instance
        )

        settings_pixelization = (
            self.settings.settings_pixelization.settings_with_is_stochastic_true()
        )

        log_evidences = []

        for i in range(histogram_samples):

            try:
                log_evidence = fit.FitImaging(
                    masked_imaging=self.masked_dataset,
                    tracer=tracer,
                    hyper_image_sky=hyper_image_sky,
                    hyper_background_noise=hyper_background_noise,
                    settings_pixelization=settings_pixelization,
                    settings_inversion=self.settings.settings_inversion,
                ).log_evidence
            except (InversionException or GridException) as e:
                log_evidence = None

            if log_evidence is not None:
                log_evidences.append(log_evidence)

        return log_evidences

    def visualize(self, instance, during_analysis):

        instance = self.associate_hyper_images(instance=instance)
        tracer = self.tracer_for_instance(instance=instance)
        hyper_image_sky = self.hyper_image_sky_for_instance(instance=instance)
        hyper_background_noise = self.hyper_background_noise_for_instance(
            instance=instance
        )

        fit = self.masked_imaging_fit_for_tracer(
            tracer=tracer,
            hyper_image_sky=hyper_image_sky,
            hyper_background_noise=hyper_background_noise,
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

        try:
            visualizer.visualize_ray_tracing(
                tracer=fit.tracer, during_analysis=during_analysis
            )
            visualizer.visualize_fit(fit=fit, during_analysis=during_analysis)
        except Exception:
            pass

        if not during_analysis and visualizer.plot_stochastic_histogram:

            log_evidences = self.stochastic_log_evidences_for_instance(
                instance=instance
            )

            visualizer.visualize_stochastic_histogram(
                log_evidences=log_evidences,
                max_log_evidence=fit.log_evidence,
                during_analysis=during_analysis,
            )
