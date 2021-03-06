=============
API Reference
=============

---------------
Data Structures
---------------

.. currentmodule:: autolens

.. autosummary::
   :toctree: generated/

   Array
   Values
   Grid
   GridIterate
   GridInterpolate
   GridCoordinates
   Kernel
   Convolver
   Visibilities
   TransformerDFT
   TransformerFFT
   TransformerNUFFT

--------
Datasets
--------

.. currentmodule:: autolens

.. autosummary::
   :toctree: generated/

   Imaging
   MaskedImaging
   Interferometer
   MaskedInterferometer

----------
Simulators
----------

.. currentmodule:: autolens

.. autosummary::
   :toctree: generated/

   SimulatorImaging
   SimulatorInterferometer

-------
Fitting
-------

.. autosummary::
   :toctree: generated/

   FitImaging
   FitInterferometer

--------------
Light Profiles
--------------

.. currentmodule:: autogalaxy.profiles.light_profiles

.. autosummary::
   :toctree: generated/

   EllipticalGaussian
   SphericalGaussian
   EllipticalSersic
   SphericalSersic
   EllipticalExponential
   SphericalExponential
   EllipticalDevVaucouleurs
   SphericalDevVaucouleurs
   EllipticalCoreSersic
   SphericalCoreSersic

-------------
Mass Profiles
-------------

.. currentmodule:: autogalaxy.profiles.mass_profiles

**Total Mass Profiles:**

.. autosummary::
   :toctree: generated/

    PointMass
    EllipticalCoredPowerLaw
    SphericalCoredPowerLaw
    EllipticalBrokenPowerLaw
    SphericalBrokenPowerLaw
    EllipticalCoredIsothermal
    SphericalCoredIsothermal
    EllipticalPowerLaw
    SphericalPowerLaw
    EllipticalIsothermal
    SphericalIsothermal

**Dark Mass Profiles:**

.. autosummary::
   :toctree: generated/

    EllipticalGeneralizedNFW
    SphericalGeneralizedNFW
    SphericalTruncatedNFW
    SphericalTruncatedNFWMCRDuffy
    SphericalTruncatedNFWMCRLudlow
    SphericalTruncatedNFWMCRChallenge
    EllipticalNFW
    SphericalNFW
    SphericalNFWMCRDuffy
    SphericalNFWMCRLudlow

**Stellar Mass Profiles:**

.. autosummary::
   :toctree: generated/

    EllipticalGaussian
    EllipticalSersic
    SphericalSersic
    EllipticalExponential
    SphericalExponential
    EllipticalDevVaucouleurs
    SphericalDevVaucouleurs
    EllipticalSersicRadialGradient
    SphericalSersicRadialGradient

**Mass-sheets:**

.. autosummary::
   :toctree: generated/

   ExternalShear
   MassSheet

-------
Lensing
-------

.. currentmodule:: autolens

.. autosummary::
   :toctree: generated/

   Galaxy
   Plane
   Tracer

----------
Inversions
----------

.. currentmodule:: autoarray.inversion.pixelizations

**Pixelizations:**

.. autosummary::
   :toctree: generated/

   Rectangular
   VoronoiMagnification
   VoronoiBrightnessImage

.. currentmodule:: autoarray.inversion.regularization

**Regularizations:**

.. autosummary::
   :toctree: generated/

   Constant
   AdaptiveBrightness

.. currentmodule:: autolens

**Inversions:**

.. autosummary::
   :toctree: generated/

   Mapper
   Inversion


-----
Plots
-----

.. currentmodule:: autolens.plot

**Plotters**

.. autosummary::
   :toctree: generated/

   Plotter
   SubPlotter
   Include

**Matplotlib Objects**

.. autosummary::
   :toctree: generated/

   Figure
   ColorMap
   ColorBar
   Ticks
   Labels
   Legend
   Units
   Output
   OriginScatterer
   MaskScatterer
   BorderScatterer
   GridScatterer
   PositionsScatterer
   IndexScatterer
   PixelizationGridScattere
   Liner
   ArrayOverlayer
   VoronoiDrawer
   LightProfileCentreScatterer
   MassProfileCentreScatterer
   MultipleImagesScatterer
   CriticalCurvesLiner
   CausticsLiner

**Plots:**

.. autosummary::
   :toctree: generated/

   Array
   Grid
   Line
   MapperObj
   Imaging
   Interferometer
   MassProfile
   LightProfile
   Galaxy
   Plane
   Tracer
   FitImaging
   FitInterferometer
   FitGalaxy
   Inversion
   Mapper

-------------
Lens Modeling
-------------

.. currentmodule:: autolens

**Phases:**

.. autosummary::
   :toctree: generated/

   PhaseImaging
   PhaseInterferometer

**Settings:**

.. autosummary::
   :toctree: generated/

   SettingsPhaseImaging
   SettingsPhaseInterferometer

**Pipelines:**

.. autosummary::
   :toctree: generated/

   PipelineDataset

**Setup:**

.. autosummary::
   :toctree: generated/

   SetupPipeline

**SLaM:**

.. currentmodule:: autolens.pipeline.slam

.. autosummary::
   :toctree: generated/

   SLaM
   SLaMHyper
   SLaMSource
   SLaMLight
   SLaMMass

---------
PyAutoFit
---------

**Searches:**

.. currentmodule:: autofit

.. autosummary::
   :toctree: generated/

   DynestyStatic
   DynestyDynamic
   Emcee
   PySwarmsGlobal
   MultiNest