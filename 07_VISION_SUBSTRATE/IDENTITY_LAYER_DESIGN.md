# Identity recognition layer - architecture (no ML implemented)

The Phoxelis Vision Language describes scenes through composable
typed predicates that produce auditable verdicts. It cannot, by
construction, recognise identities: "this face is Vince" or "this
object is a Samsung S23" or "this scene is the user's living room"
all require learned distributions over named instances. That data
does not live in the predicate substrate.

This document specifies the INTERFACE for plugging external
identity-recognition models into the language without changing the
substrate. It is design only - no model is shipped, no operators
are registered.

## What identity adds beyond the existing 96 predicates

The existing language can say:

  "It presents orange hues with a warm palette. Its structure shows
  a face-like subject and isotropic / round structure. Compositionally,
  it has a centred subject with significant negative space. Depth
  and tone: high contrast. Lighting: subject lit (centre brighter
  than edges)."

That is everything a CAREFUL HUMAN OBSERVER can describe without
recognising the subject. What it cannot say:

  "Vince is in the photo."
  "The room is the kitchen."
  "The animal is a cat, specifically a tabby."
  "The text reads 'INVOICE 0042'."

Those four sentences require IDENTITY recognition - mapping perceived
content to named instances that exist outside the predicate library.

## Architectural design

### One new dtype

  identity_label   string label returned by an external classifier,
                   distinguished from the existing `label` dtype by
                   semantics (not by storage; both are strings)

`label` dtype is used for fixed-vocabulary literals like "horizontal",
"red", "0deg". `identity_label` is used for open-vocabulary classifier
outputs that are NOT known at vocab-author time.

### One new operator family: external_classifier

  external_classifier(image|color_image, label, identity_label)
                                          ^classifier_key
                                                 ^expected_label
    -> bool

The classifier_key (e.g. "face_id", "object_class", "scene_category",
"ocr_text") names a callable registered in the runtime by the host
application. The runtime looks up the callable at evaluate time,
runs it on the image, compares its return to expected_label.

This keeps the substrate model-agnostic: no specific ML library
appears in the operator registry. The Phoxelis Workbench remains
zero-VRAM-by-default; identity becomes opt-in by registering a
callable.

### Runtime hook contract

  runtime.register_classifier(key: str, fn: Callable[[image], str])

  fn takes the image (or color_image), runs whatever model, returns
  a string identity_label. Conventional return values:
    - empty string ""  = no identity detected
    - "unknown"       = something detected but no match in the model
    - any other value = the recognised identity

### Example identity predicates (when a model is registered)

  predicate has_face_id_match
    expects color_scene:color_image, identity:identity_label
    returns bool
    intent  face_classifier_returns_expected_identity
    body    external_classifier(color_scene, "face_id", identity)

  predicate has_text_content_invoice
    expects color_scene:color_image
    returns bool
    intent  ocr_returns_invoice_marker
    body    external_classifier(color_scene, "ocr_text", "INVOICE")

These would only fire if the host has registered an "face_id" or
"ocr_text" classifier. Without the classifier registered, the
runtime returns BLOCKED (same way Bayer-dependent predicates are
BLOCKED today on JPEG-only sessions).

## What this enables AT INTERFACE LEVEL

  - Vocabulary authors can write predicates referring to identity
    concepts without committing to any specific ML model.
  - Host applications can plug in different models (CLIP / face
    recognition / OCR / segmentation) by registering callables.
  - The narrator can incorporate identity verdicts seamlessly:
    "It is a face-like subject" becomes "It is Vince" when the
    face_id classifier fires.

## What this DOES NOT do

  - No model is shipped with Phoxelis.
  - No model is registered by default.
  - No identity predicates are added to the v0.13 vocabulary.
  - No code path forces ML dependencies on consumers who only
    want the perceptual vocabulary.

## When to implement

The interface design lives here. Implementation - registering the
classifier hooks, adding the external_classifier operator, adding
identity_label to VALID_DTYPES - waits until a real ML model is
ready to plug in. The substrate is prepared for it.

## Stub composite predicates (added today)

Three composite predicates over EXISTING perceptual content
approximate identity-like categories without ML:

  has_human_subject      face_like_signature AND centre_weighted_lighting
                         AND vertical_mirror_correlation > threshold

  has_indoor_scene       low_light_signature OR center_weighted_lighting
                         AND NOT atmospheric_haze

  has_screen_subject     screen_like_signature AND centred_subject

These are not identity recognition - they are pattern composites.
They do however fire on real photos in ways that approximate what
identity recognition would describe at coarse category level.
