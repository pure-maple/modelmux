# Workflow Examples

Real-world usage patterns for multi-model collaboration.

## Example 1: Parallel Code Review

Ask Codex and Gemini to independently review the same code, then synthesize.

```
User: "Review my authentication module for security issues"

Claude workflow:
1. session.sh start code-review
2. dispatch.sh --model codex --prompt "Review auth.py for security vulnerabilities..."
   dispatch.sh --model gemini --prompt "Review auth.py for security vulnerabilities..."
3. collect.sh --wait-all
4. Synthesize: merge findings, deduplicate, rank by severity
5. session.sh stop
```

## Example 2: Sequential Pipeline — Design → Implement → Test

```
User: "Build a REST API for user management"

Claude workflow:
1. Claude designs the API spec (architecture is Claude's strength)
2. dispatch.sh --model codex --prompt "Implement this API: [spec]" --sandbox workspace-write
3. Collect codex output
4. dispatch.sh --model gemini --prompt "Write integration tests for: [implementation]"
5. Collect gemini output
6. Claude reviews and integrates everything
```

## Example 3: Consensus — Best of 3

```
User: "Implement an efficient LRU cache"

Claude workflow:
1. dispatch.sh --model codex --prompt "Implement LRU cache in Python..."
   dispatch.sh --model gemini --prompt "Implement LRU cache in Python..."
   Claude also writes its own version
2. Compare all three: correctness, performance, readability
3. Pick the best or merge the best parts
```

## Example 4: Quick Second Opinion

```
User: "Is my approach to database indexing correct?"

Claude workflow:
1. Claude forms initial opinion
2. dispatch.sh --model codex --prompt "Evaluate this indexing strategy: [code]"
3. Compare with own analysis
4. Present unified recommendation
```

## Example 5: Frontend + Backend Split

```
User: "Build a dashboard for sales data"

Claude workflow:
1. Claude designs component structure
2. dispatch.sh --model gemini --prompt "Create React dashboard components: [spec]"
   dispatch.sh --model codex --prompt "Create Express API endpoints: [spec]"
3. Collect both, ensure API contract matches
4. Claude integrates and resolves any interface mismatches
```
