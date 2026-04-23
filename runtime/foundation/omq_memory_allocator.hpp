#ifndef OMQ_MEMORY_ALLOCATOR_HPP
#define OMQ_MEMORY_ALLOCATOR_HPP

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <mutex>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace omq::runtime {

struct AllocatorTelemetry {
    size_t total_allocated = 0;
    size_t total_freed = 0;
    size_t current_usage = 0;
    size_t peak_usage = 0;
    size_t cache_hits = 0;
    size_t cache_misses = 0;
    size_t fragmentation_events = 0;

    std::string dump_stats() const {
        std::ostringstream oss;
        oss << "allocated=" << total_allocated
            << ", freed=" << total_freed
            << ", current_usage=" << current_usage
            << ", peak_usage=" << peak_usage
            << ", cache_hits=" << cache_hits
            << ", cache_misses=" << cache_misses
            << ", fragmentation_events=" << fragmentation_events;
        return oss.str();
    }
};

struct MemoryBlock {
    void* ptr = nullptr;
    size_t size = 0;
    uint64_t stream_id = 0;
    bool in_use = false;
};

class StreamCachingAllocator {
public:
    explicit StreamCachingAllocator(size_t initial_pool_size = 0)
        : max_cache_size_(initial_pool_size > 0 ? initial_pool_size * 4 : kDefaultMaxCacheSize),
          current_cache_size_(0) {
        if (initial_pool_size > 0) {
            expand_pool(initial_pool_size, 0);
        }
    }

    ~StreamCachingAllocator() {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto& block : free_list_) {
            std::free(block.ptr);
            block.ptr = nullptr;
            telemetry_.total_freed += block.size;
        }
        free_list_.clear();

        for (auto& [_, block] : active_allocations_) {
            std::free(block.ptr);
            telemetry_.total_freed += block.size;
        }
        active_allocations_.clear();

        current_cache_size_ = 0;
        telemetry_.current_usage = 0;
    }

    void* allocate(size_t size, uint64_t stream_id) {
        if (size == 0) {
            return nullptr;
        }

        std::lock_guard<std::mutex> lock(mutex_);

        const auto it = std::find_if(
            free_list_.begin(),
            free_list_.end(),
            [size, stream_id](const MemoryBlock& b) {
                return !b.in_use && b.size >= size && (b.stream_id == stream_id || b.stream_id == 0);
            }
        );

        if (it != free_list_.end()) {
            MemoryBlock block = *it;
            free_list_.erase(it);
            current_cache_size_ -= block.size;
            telemetry_.cache_hits++;

            if (block.size > size) {
                MemoryBlock remainder;
                remainder.ptr = std::malloc(block.size - size);
                remainder.size = block.size - size;
                remainder.stream_id = stream_id;
                remainder.in_use = false;
                if (remainder.ptr != nullptr) {
                    free_list_.push_back(remainder);
                    current_cache_size_ += remainder.size;
                    telemetry_.fragmentation_events++;
                }
                block.size = size;
            }

            block.stream_id = stream_id;
            block.in_use = true;
            auto [active_it, ok] = active_allocations_.emplace(block.ptr, block);
            if (!ok) {
                return nullptr;
            }
            telemetry_.current_usage += block.size;
            telemetry_.peak_usage = std::max(telemetry_.peak_usage, telemetry_.current_usage);
            return active_it->first;
        }

        telemetry_.cache_misses++;
        void* ptr = std::malloc(size);
        if (ptr == nullptr) {
            return nullptr;
        }

        MemoryBlock block{ptr, size, stream_id, true};
        active_allocations_[ptr] = block;
        telemetry_.total_allocated += size;
        telemetry_.current_usage += size;
        telemetry_.peak_usage = std::max(telemetry_.peak_usage, telemetry_.current_usage);
        return ptr;
    }

    void free(void* ptr, size_t size, uint64_t stream_id) {
        if (ptr == nullptr) {
            return;
        }

        std::lock_guard<std::mutex> lock(mutex_);
        auto it = active_allocations_.find(ptr);
        if (it == active_allocations_.end()) {
            return;
        }

        MemoryBlock block = it->second;
        active_allocations_.erase(it);
        block.in_use = false;
        block.stream_id = stream_id;
        if (size != 0) {
            block.size = size;
        }

        telemetry_.current_usage = telemetry_.current_usage > block.size
                                        ? telemetry_.current_usage - block.size
                                        : 0;

        recycle_block(&block);
    }

    const AllocatorTelemetry& get_telemetry() const { return telemetry_; }

    void garbage_collect() {
        std::lock_guard<std::mutex> lock(mutex_);
        while (!free_list_.empty() && current_cache_size_ > max_cache_size_) {
            MemoryBlock block = free_list_.back();
            free_list_.pop_back();
            current_cache_size_ = current_cache_size_ > block.size ? current_cache_size_ - block.size : 0;
            std::free(block.ptr);
            telemetry_.total_freed += block.size;
        }
    }

    bool verify_integrity() const {
        std::lock_guard<std::mutex> lock(mutex_);
        for (const auto& block : free_list_) {
            if (block.ptr == nullptr || block.in_use) {
                return false;
            }
        }
        for (const auto& [_, block] : active_allocations_) {
            if (block.ptr == nullptr || !block.in_use || block.size == 0) {
                return false;
            }
        }
        return true;
    }

private:
    static constexpr size_t kDefaultMaxCacheSize = 1ull << 30;  // 1 GiB

    mutable std::mutex mutex_;
    std::vector<MemoryBlock> free_list_;
    std::unordered_map<void*, MemoryBlock> active_allocations_;

    AllocatorTelemetry telemetry_;

    size_t max_cache_size_;
    size_t current_cache_size_;

    void expand_pool(size_t size, uint64_t stream_id) {
        void* ptr = std::malloc(size);
        if (ptr == nullptr) {
            return;
        }

        MemoryBlock block{ptr, size, stream_id, false};
        free_list_.push_back(block);
        current_cache_size_ += size;
        telemetry_.total_allocated += size;
    }

    void recycle_block(MemoryBlock* block) {
        if (block == nullptr || block->ptr == nullptr) {
            return;
        }

        if (current_cache_size_ + block->size > max_cache_size_) {
            std::free(block->ptr);
            telemetry_.total_freed += block->size;
            return;
        }

        free_list_.push_back(*block);
        current_cache_size_ += block->size;
    }
};

}  // namespace omq::runtime

#endif  // OMQ_MEMORY_ALLOCATOR_HPP
