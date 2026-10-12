# AI capabilities and third-party model licensing

## Current shipped capability

The current backend is not a generative-makeup system. Its image path is:

1. MediaPipe face landmarks locate one face.
2. OpenCV estimates a skin tone/undertone and applies bounded bilateral-filter skin smoothing.
3. InsightFace `buffalo_l` embeddings compare the original and processed image for the identity-similarity guard.
4. The backend saves the result and returns a foundation-match label.

This pipeline does not synthesize lipstick, eyeshadow, blush, foundation coverage, or a new photorealistic makeup look from a text prompt. UI/marketing must describe it as an image-enhancement preview until a generative model is integrated and validated.

## InsightFace licensing — commercial release gate

The repository pins `insightface==0.7.3` and the runtime loads `FaceAnalysis(name="buffalo_l")`.

InsightFace distinguishes the source-code license from its pretrained-model license:
- The Python library/code is MIT-licensed.
- The pretrained model packages supplied by InsightFace, including `buffalo_l`, are stated to be for non-commercial research by default. The code's MIT license does not independently grant commercial rights to the weights.

Official sources:
- [InsightFace model-zoo documentation](https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md)
- [InsightFace model licensing for commercial use](https://www.insightface.ai/solutions/face-recognition-licensing)

**Do not treat a successful build/deployment as evidence of commercial model permission.** Before charging salons or using this model commercially, obtain written commercial authorization for the exact `buffalo_l` model/version or replace it with a model whose commercial license and training-data terms have been reviewed. Record the applicable license and model checksum before unblocking that release gate.

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

- This repository has no root-level `LICENSE` file. The project owner should choose and add a license for this repository before inviting external contributions or asserting reuse rights.
- Audit transitive Python, Flutter and native dependencies before a commercial release; the InsightFace finding is a concrete blocker, not the whole software bill-of-materials review.
