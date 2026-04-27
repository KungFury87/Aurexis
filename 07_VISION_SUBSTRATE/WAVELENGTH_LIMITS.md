# Wavelength identification limits in this substrate

What an RGB phone sensor CAN do, what it CANNOT do, and where the
hardware unlocks live.

## What humans actually do

The human eye does not "see wavelengths" directly. It has three cone
types - S (~419 nm peak), M (~531 nm peak), L (~558 nm peak). The
brain converts cone-activation ratios into perceptual hue labels.
"Red" is not a wavelength your eye reads; it is a label your brain
assigns when L cones fire much harder than M and S.

This means humans are subject to METAMERISM: two different physical
spectra can produce identical cone activations and feel the same
color. A pure 580 nm light and a 50/50 mix of 540 nm + 620 nm look
identical to humans even though their physical wavelength
distributions are completely different.

## What an RGB phone sensor does

An RGB sensor has three filter types (R, G, B) sitting over a Bayer
mosaic. Each filter integrates a broad band of wavelengths into a
single number. The bands are chosen for color reproduction, not for
matching human cones - they are different from L/M/S.

From three numbers per pixel you can:
  - convert to HSV and identify perceptual hue buckets
    (red ~625 nm, orange ~605 nm, yellow ~575 nm, green ~525 nm,
    cyan ~485 nm, blue ~445 nm, violet ~410 nm)
  - measure saturation and value
  - distinguish chromatic from achromatic pixels

You CANNOT:
  - recover specific monochromatic wavelengths (metamerism)
  - distinguish narrow spectral lines from broad mixtures producing
    the same RGB triple
  - see infrared (most phones cut at ~720 nm)
  - see ultraviolet (most phones cut below ~380 nm)
  - recover wavelength signatures the ISP averages away

## What the Vision Language currently provides

Round 10 added per-pixel HSV hue classification into 8 named buckets,
each pixel labeled absolutely (not by relative comparison) with a
peak-wavelength approximate label. This matches what human vision
labels things as. It does NOT match what a true wavelength sensor
would provide.

13 hue predicates fire on real captures, classifying scenes by their
dominant wavelength bands. has_significant_orange_hue fires on 53%
of real phone photos (warm indoor lighting, skin tones, paper), 
has_significant_blue_hue fires on 53% (sky, screens, cool light).

## What unlocks more wavelength signal

The Vision Language already documents three BLOCKED predicates that
require hardware not present in the current harness:

  has_subpixel_periodicity     needs raw_bayer (pre-ISP)
  has_spectral_band_anomaly    needs raw_bayer (pre-ISP)
  has_polarization_signal      needs cap_axis_0 / cap_axis_90 pair

This document adds a fourth class of BLOCKED predicates - true
wavelength resolution beyond RGB - which would require:

  multispectral_anomaly_score  needs >3 spectral bands per pixel
  hyperspectral_signature      needs ~30+ narrow bands per pixel
  ir_signature                 needs IR-passable filter (most phones
                                 have a hot mirror that cuts IR)
  uv_signature                 needs UV-passable filter

The hardware path: a multispectral camera module (e.g. AMS Liquid
Lens with tunable filter, or a 4-band RGB+NIR add-on) attached to
the phone or a separate lab capture rig, exporting per-band frames
that the harness ingests as a multispectral_stack image dtype.

## Honest framing

The current vocabulary's hue predicates do what human vision does:
absolute named-color identification from a 3-band sensor. That is
a legitimate model of "seeing color" - it is what the eye does, just
through different filters than human cones.

It is not a model of "knowing the wavelength" in the strict
spectroscopic sense. For that, the project needs multispectral
hardware, and this is a known unlock parallel to the raw Bayer +
polarization unlocks already documented.

Vision Language v0.6 is wavelength-aware to the precision a 3-band
sensor permits, and is structured so adding a multispectral_image
dtype + spectroscopic operators is one round of work when the
hardware shows up.
