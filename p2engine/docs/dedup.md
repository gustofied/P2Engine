# Deduplication Policies

P2Engine provides three deduplication policies to handle duplicate tool calls:

- **NoDedupPolicy** – no deduplication; every tool call runs (default in development).
- **PenaltyDedupPolicy** – duplicate calls are _allowed_ but logged and metric-emitted.
- **StrictDedupPolicy** – duplicate calls are blocked _unless_ the tool is marked
  as `side_effect_free`.

All deduplication logic lives exclusively inside these policy classes and is
executed by the `EffectExecutor`. **No other duplicate guards exist anywhere in
the runtime.**

## Configuring the Deduplication Policy

Set `DEDUP_POLICY` in the environment:

| Value     | Active policy             |
| --------- | ------------------------- |
| `none`    | `NoDedupPolicy` (default) |
| `penalty` | `PenaltyDedupPolicy`      |
| `strict`  | `StrictDedupPolicy`       |

## Marking Tools as Side-Effect-Free

Tools can opt-out of strict blocking by declaring themselves side-effect-free:

```python
@function_tool(
    name="example_tool",
    description="An example tool",
    side_effect_free=True,
)
def example_tool():
    ...
```
