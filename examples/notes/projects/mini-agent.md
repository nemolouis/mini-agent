# mini-agent

Status: M1 and M3 done, M4 (this MCP server) in progress.

## Open problems
- Context compaction runs on every step when the limit is tiny (see failure case 2).
- Models often stop after a green *visible* test run although the spec says more (failure case 13).

## Links
- Evaluation tasks live in `tasks/`; hidden tests are never shown to the agent.
