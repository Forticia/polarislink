# polarislink (C++20 client header)

Single-header C++20 client for the PolarisLink wire protocol.

## Features

- Single header: `#include <polarislink/polarislink.hpp>`
- C++20, no mandatory third-party dependencies beyond libcurl
- Dual transport: in-process libcurl, and an isolated fallback transport

## CMake

```cmake
add_subdirectory(cpp)
target_link_libraries(your_target PRIVATE polarislink)
```

See the repository root `SPECIFICATION.md` for the protocol and `examples/cpp` for a working client.
