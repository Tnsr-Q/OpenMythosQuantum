#ifndef OMQ_DISPATCHER_HPP
#define OMQ_DISPATCHER_HPP

#include <memory>
#include <shared_mutex>
#include <string>
#include <unordered_map>

#include "omq_plugin_abi.h"

namespace omq::runtime {

class Dispatcher {
public:
    using PluginPtr = std::shared_ptr<void>;
    using ExecuteFn = OMQ_PluginExecute;

    struct PluginEntry {
        PluginPtr lib_handle;
        ExecuteFn execute_fn;
        uint32_t abi_version;
        uint32_t plugin_version;
    };

    bool register_plugin(
        const std::string& name,
        PluginPtr lib_handle,
        const OMQ_PluginInterface& iface
    ) {
        if (!iface.execute || iface.abi_version != OMQ_PLUGIN_ABI_VERSION) {
            return false;
        }

        std::unique_lock lock(registry_mutex_);
        registry_[name] = {
            std::move(lib_handle),
            iface.execute,
            iface.abi_version,
            iface.plugin_version,
        };
        return true;
    }

    bool dispatch(
        const std::string& op_name,
        DLManagedTensor* inputs,
        size_t input_count,
        DLManagedTensor* outputs,
        size_t output_count,
        void* stream = nullptr,
        void* workspace = nullptr,
        size_t workspace_size = 0
    ) const {
        std::shared_lock lock(registry_mutex_);
        auto it = registry_.find(op_name);
        if (it == registry_.end()) {
            return false;
        }

        if ((input_count > 0 && inputs == nullptr) ||
            (output_count > 0 && outputs == nullptr)) {
            return false;
        }

        const OMQ_ErrorCode err = it->second.execute_fn(
            inputs,
            input_count,
            outputs,
            output_count,
            stream,
            workspace,
            workspace_size
        );

        return err == OMQ_SUCCESS;
    }

private:
    mutable std::shared_mutex registry_mutex_;
    std::unordered_map<std::string, PluginEntry> registry_;
};

}  // namespace omq::runtime

#endif  // OMQ_DISPATCHER_HPP
