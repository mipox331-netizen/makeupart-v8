# AI capabilities and third-party model licensing

## Current shipped capability

The current backend is not a generative-makeup system. Its image path is:

1. MediaPipe face landmarks locate one face.
2. OpenCV estimates a skin tone/undertone and applies bounded bilateral-filter skin smoothing.
3. An OpenCV SSIM-style metric estimates how much facial image structure changed after smoothing. It is an image-preservation check, not biometric identity recognition.
4. The backend saves the result and returns a foundation-match label.

This pipeline does not synthesize lipstick, eyeshadow, blush, foundation coverage, or a new photorealistic makeup look from a text prompt. UI/marketing must describe it as an image-enhancement preview until a generative model is integrated and validated.

## Face-model licensing

The production image-smoothing path does not need face-recognition embeddings: MediaPipe locates facial landmarks, and OpenCV performs the bounded edit and checks structural image preservation. The implementation therefore removes the InsightFace `buffalo_l` pretrained weights and the InsightFace runtime dependency rather than using pretrained models whose published default terms restrict them to non-commercial research.

Official license references:
- [InsightFace model-zoo terms](https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md) — its pretrained model packages are non-commercial research by default.
- [MediaPipe license](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE) — Apache License 2.0.
- [OpenCV license](https://opencv.org/license/) — Apache License 2.0 for OpenCV 4.5.0 and newer.

The structural-similarity guard deliberately makes a narrower claim than face recognition. It checks that a bounded smoothing edit has not changed the local image structure too much; it does not verify a person's identity and must not be described as biometric identity protection. Because the app does not synthesize a new face or use identity embeddings, this removes the specific `buffalo_l` commercial-model licensing blocker. A complete commercial release still needs a software-bill-of-materials review of all direct/transitive dependencies and any bundled model assets.

## Generative makeup — implementation gate

A genuine generative feature needs an explicit model/provider choice and an implementation separate from the existing OpenCV filter. Before enabling it for customer photos:
- Verify commercial use rights for model weights, runtime and generated outputs.
- Capture explicit customer consent for processing and any third-party processor transfer.
- Define whether images are retained by the provider, and configure retention/deletion accordingly.
- Preserve face identity, hair, skin tone and background; validate outputs and provide a safe fallback when generation fails.
- Measure latency, infrastructure/API cost, usage quota and abuse limits before enabling it on the free plan.
- Add before/after tests across lighting, skin tones and makeup styles; do not present the feature as available until those tests pass.

No generative inference provider, model license, API credential or validated generative pipeline is configured in this repository as of this status update.

## Other license and distribution checks

- The root-level `LICENSE` now states that original project materials are proprietary and grants no general reuse permission. It does not cover third-party components; retain their notices and review the generated inventories described in [Third-party license audit](THIRD_PARTY_LICENSE_AUDIT.md).
- Audit transitive Python, Flutter and native dependencies before a commercial release; removal of the restricted InsightFace weights resolves that specific finding, not the entire software bill-of-materials review.
