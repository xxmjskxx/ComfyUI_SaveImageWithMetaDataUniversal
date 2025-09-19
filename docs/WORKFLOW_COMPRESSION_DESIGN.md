# Workflow Compression & Embedding Design (Deferred)

Status: Deferred (ideas parked for future implementation)
Owner: (unassigned)
Last Updated: 2025-09-19

## 1. Motivation
Large ComfyUI workflows (150KB–450KB+ JSON) exceed safe JPEG EXIF limits (~60KB usable) and inflate PNG or WebP metadata. We want an adaptive strategy that preserves usability while preventing save failures and avoiding brittle hacks.

## 2. Goals
- Avoid breaking existing automatic workflow reload where possible (especially for PNG).
- Keep JPEG saves reliable without throwing errors when metadata is large.
- Allow future optional embedding of compressed workflows.
- Provide clear metadata indicators when fallback or alternative storage is used.

## 3. Non-Goals (Current Phase)
- No multi-segment APPn chaining shipped yet.
- No mandatory compression (opt-in or adaptive only).
- No opaque binary blob without version header.

## 4. Constraints & Observations
| Channel | Practical Limit | Notes |
| ------- | --------------- | ----- |
| EXIF (APP1) | ~60–62 KB payload | Hard ceiling per segment. |
| JPEG COM | 64 KB per marker | Multiple allowed; may be stripped. |
| PNG zTXt/iTXt | Flexible | Size can still bloat file. |
| Workflow JSON compressibility | 30–60% of original | Depends on repetition. |
| Base64 overhead | +33% | Avoid if embedding binary is feasible. |

## 5. Proposed Adaptive Policy (Future)
1. Compute raw workflow JSON size.
2. Thresholds (configurable):
   - `compress_threshold_kb` (default 50)
   - `embed_cap_kb` (default 58 for JPEG EXIF)
3. Decision:
   - If raw ≤ compress_threshold_kb → embed raw (status quo).
   - Else gzip; if compressed ≤ embed_cap_kb → embed compressed.
   - Else store sidecar only; embed pointer + hash.
4. Optional experimental mode: Fragmented COM markers (disabled by default).

## 6. Data Formats
### 6.1 Compressed Payload Header
Binary prefix before gzip bytes:
```
WFLOW\x01 <4-byte big-endian uncompressed_len> <gzip data>
```
Rationale: Magic + version + integrity check.

### 6.2 Text (Fallback) Encoding
If binary unsafe context encountered → base64 encode gzip bytes and prefix string:
```
v1:gzip+b64:<base64>
```

## 7. Metadata Keys (Additions)
| Key | Meaning |
| --- | ------- |
| `Workflow Storage` | `raw-exif`, `compressed-exif`, `sidecar`, `fragmented-com` |
| `Workflow Original Bytes` | Uncompressed length |
| `Workflow Compressed Bytes` | Present if compressed |
| `Workflow SHA256` | Hash of raw JSON |
| `Workflow Compression Version` | `1` when using `WFLOW\x01` header |

## 8. Sidecar Strategy
Always write `basename.workflow.json` when:
- Not embedding raw OR
- Embedding compressed OR
- User enables `always_write_sidecar`.

## 9. Fragmentation (Experimental Path)
Multi-COM segmentation layout per segment:
```
WFSEG\x01 <total_segments:1> <index:1> <payload>
```
Reconstruct by collecting, validating contiguous indices, concatenating payloads, then treating as Section 6.1 header.

Risks: Stripping by image pipelines; ordering not guaranteed after some transformations.

## 10. Security & Integrity
- Store SHA256 of raw JSON to detect tampering.
- (Future) Optional signature: `Workflow Signature`, `Workflow PubKey`.

## 11. Failure Handling
If embedding step raises exception:
- Log debug.
- Drop to sidecar path.
- Still record hash and storage mode.

## 12. API / UI Additions (Future)
| Param | Type | Default | Purpose |
| ----- | ---- | ------- | ------- |
| `workflow_mode` | enum | `auto` | `auto|none|sidecar_only|force_compressed` |
| `compress_threshold_kb` | int | 50 | Start compression when exceeded |
| `embed_cap_kb` | int | 58 | Hard ceiling for embedding after compression |
| `allow_fragmentation` | bool | False | Enable multi-segment COM (experimental) |
| `always_write_sidecar` | bool | False | Redundant explicit sidecar |

## 13. Test Matrix (Planned)
| Case | Raw Size | Expected Storage | Notes |
| ---- | -------- | ---------------- | ----- |
| A | 20 KB | raw-exif | Baseline |
| B | 55 KB | compressed-exif | Post-compress shrink |
| C | 120 KB | sidecar | Too large even compressed |
| D | 55 KB + fragmentation forced | fragmented-com | Experimental |
| E | Corrupted header | sidecar + warning | Recovery |

## 14. Migration / Backward Compatibility
- Legacy images without these keys remain valid.
- Parsers should treat absence of `Workflow Storage` as `raw-exif` (implicit).

## 15. Open Questions
- Should we attempt PNG-specific larger embedding always? (Probably yes; PNG unconstrained.)
- Worth supporting zstd (better ratio) vs gzip (universally available)?
- Need limit to avoid multi-megabyte bloating of PNG metadata.

## 16. Deferred Items
- Fragmented multi-segment APPn robust implementation.
- Digital signature integration.
- zstd optional compression negotiation.

## 17. Implementation Steps (Future Ticketing)
1. Add sizing + compression utility module.
2. Insert decision logic pre-save.
3. Extend metadata dict with storage keys.
4. Sidecar writer (atomic write, `.tmp` rename).
5. Optional fragmentation (guarded + tests).
6. Test harness injecting synthetic workflow sizes.

---
This document is a design placeholder. Update when scope is accepted for implementation.
