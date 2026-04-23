#ifndef OMQ_PLUGIN_ABI_H
#define OMQ_PLUGIN_ABI_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>
#include <stdint.h>

#include <dlpack/dlpack.h>

// Increment only for breaking ABI changes.
#define OMQ_PLUGIN_ABI_VERSION 1u

// Error codes for plugin execution.
typedef enum {
    OMQ_SUCCESS = 0,
    OMQ_ERR_INVALID_SHAPE = 1,
    OMQ_ERR_UNSUPPORTED_DEVICE = 2,
    OMQ_ERR_COMPUTE_FAILURE = 3,
    OMQ_ERR_INVALID_ARGUMENT = 4
} OMQ_ErrorCode;

/**
 * @brief Signature for OMQ plugin execution.
 *
 * Plugins implement this function to be routed by the dispatcher.
 * - inputs / outputs are arrays of DLPack managed tensors.
 * - stream is an optional backend stream handle (for example cudaStream_t).
 * - workspace is an optional scratch buffer owned by the dispatcher.
 */
typedef OMQ_ErrorCode (*OMQ_PluginExecute)(
    DLManagedTensor* inputs,
    size_t input_count,
    DLManagedTensor* outputs,
    size_t output_count,
    void* stream,
    void* workspace,
    size_t workspace_size
);

/**
 * @brief OMQ plugin metadata + function table.
 */
typedef struct {
    uint32_t abi_version;
    uint32_t plugin_version;
    const char* plugin_name;
    OMQ_PluginExecute execute;
} OMQ_PluginInterface;

// Symbol to be exported by every plugin shared library.
OMQ_PluginInterface omq_plugin_create(void);

#ifdef __cplusplus
}
#endif

#endif  // OMQ_PLUGIN_ABI_H
