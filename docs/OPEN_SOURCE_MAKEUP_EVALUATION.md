# Open-source makeup-transfer model evaluation

**Decision date:** 13 October 2026  
**Constraint:** $0 recurring provider spend; protect the existing production service.

## Finding

The repository has a low-cost classic engine using MediaPipe landmarks and OpenCV image operations. A true learned makeup-transfer model can move color/texture from a reference makeup photo, but it is not equivalent to a CPU-only color overlay and generally brings a larger checkpoint, ML runtime, inference memory/compute, and separate model-license obligations.

## Candidates reviewed

| Candidate | Evidence from its project | Decision for MakeupArt V8 |
|---|---|---|
| [Stable-Makeup](https://github.com/Xiaojiu-z/Stable-Makeup) | Repository shows an Apache-2.0 code license, diffusion implementation, and checkpoint downloads via Google Drive. The README does not clearly grant separate commercial terms for the exact pretrained checkpoint. It depends on Stable Diffusion 1.5, SPIGA and facelib. | Best candidate to investigate further, but **not integrated** until checkpoint and dependency terms are independently verified and a GPU-capable inference target is available. |
| [SHMT](https://github.com/Snowfallingplum/SHMT) | Its README expressly gives CC BY-NC-SA 4.0 terms and documents inference with `CUDA_VISIBLE_DEVICES`. | Do not ship in a commercial product without a separate license grant. |
| [MagicMakeup](https://github.com/vivoCameraResearch/Magic-Makeup) | Its README describes academic-research-only intent and depends on FLUX.1-Kontext-dev, whose model terms/access must also be accepted. | Not a fit for a commercial $0 production path. |
| [MAD](https://github.com/basiclab/MAD) | Provides makeup-transfer code and a CUDA-tested environment, but no clear repository-level license grant was found in the top-level files reviewed. | Do not redistribute or deploy until the license and all model/data terms are confirmed. |

## Runtime fit

The deployed Modal function currently uses 2 CPUs and 4 GB RAM and does not install PyTorch/diffusers or download a makeup-transfer checkpoint. That is not proof that diffusion inference can run reliably on the current production instance. Moving inference to a GPU-backed host could introduce hosting costs, so it would violate the user's $0 requirement unless a genuinely free and sustainable target is verified.

## Implemented $0 alternative

The Classic engine remains the active path and does not send portraits to OpenAI or another image provider. It now applies face-mesh-guided lipstick, cheek blush, upper-eye shadow and a small style-dependent eyeliner/wing for its four existing presets. It is still deterministic image-space editing, not generative makeup transfer, hairstyle synthesis, or guaranteed FaceApp-quality output.

## Safe next gate for model adoption

A model can be integrated only after all four checks pass:

1. Confirm a license grant for the exact model weights, source code, base model, preprocessing assets and runtime dependencies that matches the intended use.
2. Prove inference on a target that costs $0 to operate on an ongoing basis, with measured latency and memory on actual deployment limits.
3. Run a consenting and properly licensed evaluation set across skin tones, lighting, pose, glasses, facial hair and makeup styles; compare identity/detail preservation and face-region leakage.
4. Keep the production default on Classic until those tests pass. Never silently send customers' faces to a third-party provider or advertise generative capabilities when a provider is not configured.

This document records an engineering review, not legal advice or proof of model quality.
