# JPEG Metadata Fallback & Size Guidance

Status: Implemented (multi-stage fallback); fragmentation & compression pipeline deferred.
Last Updated: 2025-09-19

## 1. Why This Exists
Prompt + workflow + hash detail can exceed the practical single APP1 (EXIF) capacity in JPEG (~60–64KB usable). Oversized blocks risk:
- Silent truncation by some decoders or hosting platforms.
- Stripping by optimization/CDN pipelines.
- Save errors (rare) or very slow writes when fragmented.

The node applies staged degradation rather than failing outright so a usable parameters string is always embedded somehow.

## 2. Fallback Stages
| Stage | Trigger | What Is Embedded | Pros | Cons |
|-------|---------|------------------|------|------|
| full | ≤ `max_jpeg_exif_kb` limit | Full EXIF (workflow JSON + parameters + hashes) | Richest data | Larger file, risk of stripping |
| reduced-exif | Full EXIF > limit | EXIF with parameters-only `UserComment` | Retains structured EXIF container | Workflow JSON lost |
| minimal | Reduced still > limit | Trimmed parameter subset (core fields, LoRAs, hashes) | Keeps essentials, small | Some detail removed |
| com-marker | Minimal still > limit OR builder failure | Plain parameters string in JPEG COM marker | Always succeeds, tiny | Unstructured; may be stripped |

The active stage is appended to the parameter line as: `Metadata Fallback: <stage>` for any stage other than `full`.

## 3. Parameter Trimming (Minimal Stage)
Kept keys:
- Prompts (positive / negative)
- Steps, Sampler, CFG scale / Guidance (depending on `guidance_as_cfg`)
- Seed, Model, Model hash, VAE, VAE hash
- All `Lora_*` entries (names, hashes, strengths)
- Hashes summary line
- Metadata generator version

Removed keys include batch index/size, size, weight dtype, auxiliary internal or experimental fields.

## 4. Choosing `max_jpeg_exif_kb`
| Use Case | Recommendation |
|----------|----------------|
| Maximum compatibility (email, social sites) | 48–56 |
| Balanced (retain most metadata) | 60 (default) |
| Aggressive (try to keep full workflow) | 64 (risk: truncation) |
| Highly custom archiving (not advised) | >64 (little benefit; risk grows) |

Raising the limit above ~64 rarely helps because the segment hard cap remains; giant metadata is better preserved in PNG.

## 5. When To Prefer Other Formats
- Need guaranteed full workflow: Use PNG.
- Lossless but smaller vs PNG: Use WebP `lossless_webp=True` (no same EXIF constraint).
- Distribution copy only: JPEG with fallback is fine.

## 6. Detection & Tooling
To detect fallback stage programmatically parse the parameter string tail token. Example pseudo:
```python
if ", Metadata Fallback:" in params:
    stage = params.rsplit("Metadata Fallback:", 1)[1].strip()
```

Future enhancement may expose an explicit `Metadata Fallback` EXIF tag or sidecar JSON key.

## 7. Future Roadmap (Deferred)
Planned ideas (see `WORKFLOW_COMPRESSION_DESIGN.md` for details):
- Optional gzip compression & embedding of compressed workflow (size + hash keys).
- Multi-COM fragmentation (experimental; off by default) with integrity reconstruction.
- Sidecar pointer + hash strategy for extremely large workflows.
- zstd support as optional higher ratio compressor.

## 8. FAQ
**Q: Why is my workflow missing when I open a JPEG?**  
Because the save exceeded the size limit and fell back to reduced or minimal EXIF. Use PNG or lower workflow complexity.

**Q: Can I recover data from a `com-marker` stage?**  
Yes—prompt + essential generation settings remain; workflow graph JSON is not stored.

**Q: Does lowering `max_jpeg_exif_kb` hurt anything?**  
Only richness of embedded metadata; image pixels unaffected.

**Q: Are multiple EXIF segments chained?**  
Not currently; fragmentation is deferred to avoid viewer incompatibilities.

---
For contribution discussions open an issue referencing this document.
