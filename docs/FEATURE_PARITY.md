# MakeupArt V8 — Face Editor Feature Parity

**Review date:** 10 November 2026  
**Scope:** Current repository source on `fix/production-api-config-and-storage-gates`. This is a source-code capability review, not a claim that every feature has passed a physical-device test or is live in production.

## Reference benchmark

FaceApp's current product pages describe realistic one-tap portrait edits, including retouching, impression, makeup, hair volume, hair color, hairstyles, beard, age/gender changes, facial-feature adjustments and before/after comparison. Its June 2026 filter guide groups tools into 12 folders: Impression, Skin, Sizes, Hairstyles, Hair Colors, Smiles, Features, Beards, Makeup, Age, Gender and Glasses. FaceApp also documents favorites, multi-select filter layering and reusable presets.

YouCam Makeup is a broader makeup-first comparison: it documents live-camera virtual makeup, per-feature makeup controls, face retouch, hairstyle and hair-color try-on, body tools and AI creative features. These are product benchmarks, not features that MakeupArt can claim by resemblance alone.

References:
- https://www.faceapp.com/
- https://www.faceapp.com/blog/meet-your-face-filters/
- https://play.google.com/store/apps/details?id=io.faceapp
- https://www.perfectcorp.com/consumer/apps/yucam-makeup
- https://www.youcammakeup.com/consumer/features/makeup-editor

## Current source capability matrix

| Capability | MakeupArt V8 source state | Notes |
|---|---|---|
| Import from gallery | Implemented | JPEG, PNG and WebP uploads are validated by the API. |
| Capture with camera | Implemented | Uses the platform camera picker; it is capture-then-edit, not live virtual makeup. |
| Face-aware makeup | Implemented | MediaPipe face landmarks drive local lipstick, blush, eyeshadow and eyeliner overlays. |
| Makeup presets | Implemented | Natural, Soft Glam, Bridal Rose, Evening Glam and targeted eye/lip/cheek looks. Actual options remain plan-entitled by the backend. |
| Skin polish | Implemented | Face-region smoothing with a strength control; it is not a generative facelift. |
| Photo finishes | Implemented | Natural Finish, Warm Glow, Soft Glam, Studio Polish and Golden Hour. |
| Manual photo adjustments | Implemented in this branch | Server-side brightness, contrast, saturation, warmth and sharpness controls are applied before the salon watermark. |
| Before/after comparison | Implemented | Interactive comparison divider. |
| Salon watermark/logo | Implemented | Server-side salon watermark settings are applied to the saved output. |
| Export to phone gallery | Implemented | Saves the processed PNG to the device gallery. |
| Recent results and phone backup | Implemented | Ten most recent local results remain in salon-scoped app history; every processed output is also copied to the Android `Pictures/MakeupArtV8` MediaStore folder. When the salon workspace opens or resumes, the app silently retries any pending Gallery copies; Settings also provides a manual retry for locally retained images. This is on-device storage, not off-device disaster recovery. |
| Reusable salon look presets | Implemented | Up to 24 device-local recipes; this branch also stores the five manual adjustment values and reads old presets with safe defaults. |
| Client profiles and consent | Implemented | Per-salon client profiles and stored consent; processing requires fresh operator confirmation for the selected photo. |
| Hairstyle try-on | Conditional / not release-verified | Requires a configured external generative-image provider, an eligible plan and separate external-processing consent. It is not available as an offline Classic feature. |
| Hair color preview | Implemented as a local approximation | Face-mesh-bounded head-cap recoloring for black, brown, auburn and blonde. It is not semantic hair segmentation; edge quality depends on lighting, hair visibility and background. |
| Age-style effects | Implemented as local cosmetic finishes | Youthful Finish uses face-region bilateral smoothing; Mature Finish adds fine-line overlays. Neither generates a different biological age. |
| Gender presentation | Implemented as presentation presets | Feminine Style adds local blush/lip styling; Masculine Style adds stubble/brow styling. These presets do not infer or change gender identity. |
| Facial reshaping / sizes | Implemented as subtle 2-D mesh warps | Slim Face and V-Shape locally warp the lower-face region. These are bounded 2-D previews, not 3-D or generative anatomy edits. |
| Smile editing | Implemented as a local mouth-corner warp | Soft Smile applies a bounded landmark-guided remap; it cannot synthesize teeth or a new expression. |
| Beard / mustache | Implemented as local overlays | Stubble, short/full beard and mustache are landmark-bounded overlays, not hair-by-hair generation. |
| Glasses try-on | Implemented as vector frame overlays | Round, square and aviator frames follow eye landmarks. Lens/temple occlusion is approximate, not a full 3-D try-on pipeline. |
| Multi-select filter stacking | Not implemented as a user workflow | Filters are selected as one recipe per processing run. |
| Favorite filters / favorite gallery | Not implemented in current main flow | Local salon presets are not the same as filter favorites. |
| Live camera makeup preview | Not implemented | Camera capture is supported, but the camera feed is not overlaid with live face makeup. |
| AI image/video generation | Not release-verified | External image generation requires provider credentials and can incur usage charges. No video-generation pipeline is included. |
| Automatic mobile-money collection | Not connected | Vodacom, Tigo and Airtel are selection/request options; this is not payment processing or proof of payment. |

## Product decision

MakeupArt V8 now has a broader **salon makeup and local portrait-effects workflow**, but it is still not full FaceApp feature parity. The newly added hair-color, smile, beard, glasses, face-shape and age/presentation effects are deterministic 2-D edits; they must not be marketed as generative transformations. Its strengths remain salon-scoped client handling, consent checks, makeup tools, watermarking, before/after review, export, recent local history and reusable salon recipes.

The most useful next feature phases are:

1. Improve hair segmentation and recoloring with a dedicated segmentation model and edge-quality tests; the current head-cap recolor is an approximation.
2. Replace vector glasses, beard and smile overlays with segmentation/3-D fitting where production quality requires it.
3. Add a hairstyle and true age/presentation generation provider only after provider availability, price limits, privacy disclosure and external consent are production-verified.
4. Add filter favorites and multi-select/stacking with repeatable undo/reset behavior.

**Release rule:** a filter is marked available only when its processor exists, changes the intended pixels, has automated tests, respects salon isolation/consent/plan rules, and is verified in the production build. A roadmap folder must never be presented as a working edit.
