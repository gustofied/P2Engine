# Commands

run p2engine:

```bash
./scripts/run_project.sh
```

flush Redis database:

```bash
redis-cli -h localhost -p 6379 FLUSHDB
```

repomix

```bash
## FULL
repomix . --style xml \
        --ignore '**/README.md,legacy.xml,save_staged_xml.py,staged_changes.xml,docs' \
        --remove-comments --remove-empty-lines \
        --token-count-encoding o200k_base \
        > p2engine_repomix.xml

## BESPOKE CHOICE

repomix . --style xml \
        --ignore '**/README.md,legacy.xml,save_staged_xml.py,staged_changes.xml,docs,infra/evals,cli,infra/clients,runtime/policies' \
        --remove-comments --remove-empty-lines \
        --token-count-encoding o200k_base \
        --no-directory-structure \
        > p2engine_repomix.xml

## JUST DIRECTROY

repomix . --style xml \
        --ignore '**/README.md,legacy.xml,save_staged_xml.py,staged_changes.xml' \
        --remove-comments --remove-empty-lines \
        --token-count-encoding o200k_base \
        --no-files \
        > p2engine_repomix.xml


## COMPRESSED

repomix   --style xml \
        --ignore '**/README.md,legacy.xml,save_staged_xml.py,staged_changes.xml' \
        --remove-comments --remove-empty-lines \
        --compress \
        --token-count-encoding o200k_base \
        > p2engine_repomix.xml
```

lines per file

```bash

find . -name '*.py' | xargs wc -l
```

diff

```bash
python save_staged_xml.py
```

runs

```bash

# simplest form – run everything and stream live results
poetry run p2engine rollout start config/rollout_joke.yml -f

# example : rollout start config/rollout_joke.yml -f
# example : rollout start config/demo_rollout.yml -f

# other useful flags
#   --parallel 8      : enqueue variants in chunks of 8
#   --strict-tools    : fail fast if a persona template references tools
#                       that are not enabled in the variant
#   --nowait          : fire-and-forget; don’t tail results
#   --show-config     : expand all variant combinations and exit
#   --refresh 1.0     : polling interval while following (seconds)

```

Logging

```bash
export LITELLM_LOG_LEVEL=info    # or "debug" / "error"
```

Ledger

```bash
daml build
./scripts/setup_canton.sh
```

```bash

# Check agent balance
p2engine ledger balance <agent_id>

# Transfer funds between agents
p2engine ledger transfer <from_agent> <to_agent> <amount> --reason "Test transfer"

# View transaction history
p2engine ledger history <agent_id> --limit 20

# Initialize all agent wallets
p2engine ledger init --balance 100.0

# View system-wide metrics
p2engine ledger metrics

# View ledger audit trail
p2engine ledger audit --limit 50

```
