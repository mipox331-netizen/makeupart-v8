# MakeupArt V8 — Face Editor Feature Parity

**Review date:** 2 November 2026  
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
| Recent results and phone backup | Implemented | Ten most recent local results remain in salon-scoped app history; every processed output is also copied to the Android `Pictures/MakeupArtV8` MediaStore folder. Settings provides a manual retry for locally retained images. This is on-device storage, not off-device disaster recovery. |
| Reusable salon look presets | Implemented | Up to 24 device-local recipes; this branch also stores the five manual adjustment values and reads old presets with safe defaults. |
| Client profiles and consent | Implemented | Per-salon client profiles and stored consent; processing requires fresh operator confirmation for the selected photo. |
| Hairstyle try-on | Conditional / not release-verified | Requires a configured external generative-image provider, an eligible plan and separate external-processing consent. It is not available as an offline Classic feature. |
| Hair color | Not implemented | No verified local hair segmentation/recoloring processor. |
| Age transformation | Not implemented | No age-generation model is included in the Classic engine. |
| Gender/presentation transformation | Not implemented | No transformation model is included. |
| Facial reshaping / sizes | Not implemented | The identity-preservation score is not a face-shape editing tool. |
| Smile editing | Not implemented | No expression transformation is included. |
| Beard / mustache generation | Not implemented | No beard segmentation or synthesis processor is included. |
| Glasses try-on | Not implemented | No glasses asset fitting/occlusion pipeline is included. |
| Multi-select filter stacking | Not implemented as a user workflow | Filters are selected as one recipe per processing run. |
| Favorite filters / favorite gallery | Not implemented in current main flow | Local salon presets are not the same as filter favorites. |
| Live camera makeup preview | Not implemented | Camera capture is supported, but the camera feed is not overlaid with live face makeup. |
| AI image/video generation | Not release-verified | External image generation requires provider credentials and can incur usage charges. No video-generation pipeline is included. |
| Automatic mobile-money collection | Not connected | Vodacom, Tigo and Airtel are selection/request options; this is not payment processing or proof of payment. |

## Product decision

MakeupArt V8 currently has a credible **salon makeup and photo-finishing workflow**, not full FaceApp feature parity. Its strengths are salon-scoped client handling, consent checks, makeup tools, watermarking, before/after review, export, recent local history and reusable salon recipes.

The most useful next feature phases are:

1. Add a true filter-favorites and multi-select/stacking workflow with repeatable undo/reset behavior.
2. Implement hair segmentation and recoloring with measurable edge-quality tests.
3. Add a hairstyle/image-generation provider only after provider availability, price limits, privacy disclosure and external consent are production-verified.
4. Build face reshaping, age, smile, beard and glasses as separate, tested processors; do not expose them as working tools until each produces a real image change and passes regressions.

**Release rule:** a filter is marked available only when its processor exists, changes the intended pixels, has automated tests, respects salon isolation/consent/plan rules, and is verified in the production build. A roadmap folder must never be presented as a working edit.
