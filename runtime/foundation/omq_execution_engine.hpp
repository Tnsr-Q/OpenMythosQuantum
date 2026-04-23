#ifndef OMQ_EXECUTION_ENGINE_HPP
#define OMQ_EXECUTION_ENGINE_HPP

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <unordered_map>

#if __has_include(<cuda_runtime.h>)
#include <cuda_runtime.h>
#define OMQ_HAS_CUDA_RUNTIME 1
#else
#define OMQ_HAS_CUDA_RUNTIME 0
using cudaStream_t = void*;
using cudaEvent_t = void*;
using cudaGraph_t = void*;
using cudaGraphExec_t = void*;
#endif

namespace omq::runtime {

class ExecutionStream {
public:
    explicit ExecutionStream(uint64_t id) : stream_id_(id), stream_(nullptr), capturing_(false) {
#if OMQ_HAS_CUDA_RUNTIME
        if (cudaStreamCreateWithFlags(&stream_, cudaStreamNonBlocking) != cudaSuccess) {
            throw std::runtime_error("Failed to create CUDA stream");
        }
#else
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    ~ExecutionStream() {
#if OMQ_HAS_CUDA_RUNTIME
        for (auto& [_, event] : events_) {
            cudaEventDestroy(event);
        }
        if (stream_) {
            cudaStreamDestroy(stream_);
        }
#endif
    }

    uint64_t id() const { return stream_id_; }
    cudaStream_t handle() const { return stream_; }

    void memcpy_d2d(void* dst, const void* src, size_t count) {
#if OMQ_HAS_CUDA_RUNTIME
        if (cudaMemcpyAsync(dst, src, count, cudaMemcpyDeviceToDevice, stream_) != cudaSuccess) {
            throw std::runtime_error("cudaMemcpyAsync d2d failed");
        }
#else
        (void)dst;
        (void)src;
        (void)count;
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    void memcpy_h2d(void* dst, const void* src, size_t count) {
#if OMQ_HAS_CUDA_RUNTIME
        if (cudaMemcpyAsync(dst, src, count, cudaMemcpyHostToDevice, stream_) != cudaSuccess) {
            throw std::runtime_error("cudaMemcpyAsync h2d failed");
        }
#else
        (void)dst;
        (void)src;
        (void)count;
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    void memcpy_d2h(void* dst, const void* src, size_t count) {
#if OMQ_HAS_CUDA_RUNTIME
        if (cudaMemcpyAsync(dst, src, count, cudaMemcpyDeviceToHost, stream_) != cudaSuccess) {
            throw std::runtime_error("cudaMemcpyAsync d2h failed");
        }
#else
        (void)dst;
        (void)src;
        (void)count;
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    void record_event(uint64_t event_id) {
#if OMQ_HAS_CUDA_RUNTIME
        cudaEvent_t event = nullptr;
        if (auto it = events_.find(event_id); it != events_.end()) {
            event = it->second;
        } else {
            if (cudaEventCreateWithFlags(&event, cudaEventDisableTiming) != cudaSuccess) {
                throw std::runtime_error("Failed to create CUDA event");
            }
            events_[event_id] = event;
        }

        if (cudaEventRecord(event, stream_) != cudaSuccess) {
            throw std::runtime_error("Failed to record CUDA event");
        }
#else
        (void)event_id;
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    void wait_for_event(uint64_t event_id) {
#if OMQ_HAS_CUDA_RUNTIME
        auto it = events_.find(event_id);
        if (it == events_.end()) {
            throw std::runtime_error("Event ID not recorded");
        }
        if (cudaStreamWaitEvent(stream_, it->second, 0) != cudaSuccess) {
            throw std::runtime_error("Failed to wait for CUDA event");
        }
#else
        (void)event_id;
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    void synchronize() {
#if OMQ_HAS_CUDA_RUNTIME
        if (cudaStreamSynchronize(stream_) != cudaSuccess) {
            throw std::runtime_error("Failed to synchronize CUDA stream");
        }
#else
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    void begin_capture() {
#if OMQ_HAS_CUDA_RUNTIME
        if (capturing_) {
            throw std::runtime_error("Capture already in progress");
        }
        if (cudaStreamBeginCapture(stream_, cudaStreamCaptureModeGlobal) != cudaSuccess) {
            throw std::runtime_error("Failed to begin CUDA graph capture");
        }
        capturing_ = true;
#else
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    void end_capture() {
#if OMQ_HAS_CUDA_RUNTIME
        if (!capturing_) {
            throw std::runtime_error("Capture not in progress");
        }
        cudaGraph_t graph = nullptr;
        if (cudaStreamEndCapture(stream_, &graph) != cudaSuccess) {
            capturing_ = false;
            throw std::runtime_error("Failed to end CUDA graph capture");
        }
        capturing_ = false;
        captured_graph_ = graph;
        return;
#else
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    bool is_capturing() const { return capturing_; }
    cudaGraph_t captured_graph() const { return captured_graph_; }

private:
    uint64_t stream_id_;
    cudaStream_t stream_;
    bool capturing_;
    std::unordered_map<uint64_t, cudaEvent_t> events_;
    cudaGraph_t captured_graph_ = nullptr;
};

class CUDAGraph {
public:
    explicit CUDAGraph(cudaGraph_t graph) : graph_(graph), instance_(nullptr) {
        if (graph_ == nullptr) {
            throw std::runtime_error("Graph is null");
        }
    }

    ~CUDAGraph() {
#if OMQ_HAS_CUDA_RUNTIME
        if (instance_) {
            cudaGraphExecDestroy(instance_);
        }
        if (graph_) {
            cudaGraphDestroy(graph_);
        }
#endif
    }

    void instantiate() {
#if OMQ_HAS_CUDA_RUNTIME
        if (instance_ != nullptr) {
            return;
        }
        if (cudaGraphInstantiate(&instance_, graph_, nullptr, nullptr, 0) != cudaSuccess) {
            throw std::runtime_error("Failed to instantiate CUDA graph");
        }
#else
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    void replay(uint64_t stream_id = 0) {
#if OMQ_HAS_CUDA_RUNTIME
        if (instance_ == nullptr) {
            instantiate();
        }
        (void)stream_id;
        if (cudaGraphLaunch(instance_, nullptr) != cudaSuccess) {
            throw std::runtime_error("Failed to launch CUDA graph");
        }
#else
        (void)stream_id;
        throw std::runtime_error("CUDA runtime not available");
#endif
    }

    cudaGraphExec_t instance() const { return instance_; }

private:
    cudaGraph_t graph_;
    cudaGraphExec_t instance_;
};

}  // namespace omq::runtime

#endif  // OMQ_EXECUTION_ENGINE_HPP
