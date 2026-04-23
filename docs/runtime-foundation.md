# Runtime Foundation (Phase A)

This document introduces the Phase A runtime artifacts for plugin interoperability and dynamic operator routing.

## 1) Stable C ABI plugin boundary

Header: `runtime/foundation/omq_plugin_abi.h`

Key design points:

- C linkage entrypoint `omq_plugin_create()` for stable dynamic loading.
- Zero-copy tensor handoff via `DLManagedTensor` from DLPack.
- Explicit `input_count` / `output_count` fields in `OMQ_PluginExecute` for safer dispatch.
- Versioning fields:
  - `OMQ_PLUGIN_ABI_VERSION` (global ABI)
  - `plugin_version` (plugin-specific evolution)
- `workspace` + `workspace_size` preserved for temporary allocations.

## 2) Schema-lite dispatcher and registry

Header: `runtime/foundation/omq_dispatcher.hpp`

Key design points:

- Thread-safe registry (`std::shared_mutex`) with O(1)-average lookup (`std::unordered_map`).
- ABI-gated registration: dispatcher rejects incompatible plugin ABI versions.
- Minimal schema checks in dispatch path:
  - operation exists,
  - non-null tensor arrays when count > 0.
- Dynamic routing by operation name to plugin execute function.

## 3) Verification notes

### ABI review guidance

Current ABI is sufficient for CPU/CUDA plugin execution and temporary scratch space.

For Phase B (allocator-aware execution), we can add an optional `allocator_context` pointer to an extended interface struct (`OMQ_PluginInterfaceV2`) while keeping V1 intact for backward compatibility.

### DLPack handoff / zero-copy

`DLManagedTensor` is a metadata + data-pointer contract. Zero-copy is preserved when producer and consumer agree to share ownership and avoid materializing new buffers.

### Dispatcher checks

Schema-lite is adequate for an initial fast path. For production hardening, add optional pre-dispatch validation hooks for dtype, device, shape, and contiguity policy.
