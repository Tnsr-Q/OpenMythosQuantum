# Plugin SDK Helpers

`plugins/sdk` provides lightweight base classes and helpers for building
plugins with consistent payload validation and runtime metadata handling.

## Components

- `PluginContext` — structured runtime context.
- `PluginBase` — abstract base class for plugin implementations.
- `CapabilityPlugin` — capability-aware subclass with `supports()` helper.
- `require_fields()` — validate required payload keys.
- `now_ms()` — stable epoch-millis utility for plugin responses.
