## [0.1.25] - 2026-01-22
### Added
- add to_runnable decorator
- lcc tool message add name and tool_call_id
- support set finish time of span

## [0.1.24] - 2026-01-16
### Added
- client init set default client if not exist

## [0.1.23] - 2026-01-07
### Added
- lcc support child_of and state_span_ctx_key
- lcc support multi clients
- llc support get trace_id and root_span_id

## [0.1.22] - 2026-01-06
### Added
- support span discard

## [0.1.21] - 2025-12-23
### Added
- runtime scene support get from env

## [0.1.20] - 2025-12-08
### Added
- langchain callback support langchain V1
- langchain callback support set tag and name

## [0.1.19] - 2025-11-10
### Fixed
- fix baggage escape problem
- enhance input tool_calls obtain

## [0.1.18] - 2025-10-10
### Added
- fix prompt syntax error, use Union instead of |

## [0.1.17] - 2025-10-10
### Added
- fix trace spec ModelInput field name, from model_tool_choice to tool_choice

## [0.1.16] - 2025-09-24
### Added
- support custom trace connect ptaas trace
- fix async ptaas httpclient, modify to use AsyncClient

## [0.1.15] - 2025-09-17
### Added
- modify cachetools version to >=5.5.2,<7.0.0

## [0.1.14] - 2025-09-11
### Added
- trace support openai wrapper

## [0.1.13] - 2025-09-10
### Added
- support prompt as a service (PTaaS)


## [0.1.2] - 2025-04-07

First release of cozeloop sdk.
It contains function for prompt_hub and trace.

### Added

- Initial cozeloop trace specific.
- Initial cozeloop trace and prompt_hub SDK packages.
- Example code for trace of large_text, multi_modality, parent_child, prompt and etc.
- Example code for prompt_hub.
- Exporters code for trace.
- Project guidelines and other information and  in the form of a README and CONTRIBUTING.
- MIT license.