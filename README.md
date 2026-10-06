# PolarisLink

An open protocol and reference clients for governed multi-agent coordination, telemetry and provenance.

- Wire protocol: REST plus Server-Sent Events, scoped API keys, an audit trail for every run
- Reference clients: a single-header C++20 client (`cpp/`) and a Python client (`python/`)
- Specification: [SPECIFICATION.md](SPECIFICATION.md)
- Licence: Apache-2.0

The protocol is domain-agnostic: it coordinates agents, research systems and human approvers. The clients in this repository include an example domain module for market data; other domains implement their own adapters against the same wire contract.

A hosted gateway is operated by Forticia Research Institute (https://forticia.uk/polarislink). Access to the hosted gateway requires an approved key; the protocol and the clients are open.

## Layout

- `SPECIFICATION.md`: the protocol
- `cpp/`: C++20 header-only client and tests
- `python/`: Python client and tests
- `examples/`: runnable examples

## Contributing

Issues and pull requests are welcome. Please do not include credentials, account identifiers or private data in issues or examples.
