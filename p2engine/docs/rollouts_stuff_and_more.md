some commands, experimental ways to test

# Now run the rollouts

rollout start config/rollout_joke.yml
rollout start config/demo_rollout.yml
rollout start config/rollout_task_with_payment.yml
rollout start config/rollout_competitive_payment.yml
rollout start config/rollout_hierarchical_distribution.yml

ledger overview
ledger audit

## 0.1 Basic Test

# Initialize wallets

p2engine ledger init --balance 100.0

# Check balances

p2engine ledger balance agent_alpha
p2engine ledger balance agent_beta

# Transfer funds

p2engine ledger transfer agent_alpha agent_beta 25.0 --reason "Test transfer"

# Check balances again

p2engine ledger balance agent_alpha
p2engine ledger balance agent_beta

# View history

p2engine ledger history agent_alpha
p2engine ledger history agent_beta

## 1. **System Setup & Verification**

```bash
# Start the system
./scripts/run_project.sh

# Debug Canton connection
p2engine ledger debug

# Initialize all wallets
p2engine ledger init --balance 100.0

# Check system metrics
p2engine ledger metrics
```

## 2. **Direct CLI Ledger Commands**

### Balance Operations

```bash
# Check any agent's balance
p2engine ledger balance agent_alpha
p2engine ledger balance treasurer
p2engine ledger balance agent_helper

# Check all balances via metrics
p2engine ledger metrics
```

### Transfer Operations

```bash
# Basic transfers
p2engine ledger transfer agent_alpha agent_beta 25
p2engine ledger transfer treasurer agent_helper 50 --reason "Initial funding"
p2engine ledger transfer agent_alpha child 10 -r "Allowance"

# Complex transfers
p2engine ledger transfer agent_beta agent_alpha 15 --reason "Repayment"
```

### History & Audit

```bash
# Transaction history
p2engine ledger history agent_alpha
p2engine ledger history treasurer --limit 50
p2engine ledger history agent_beta -l 10

# Audit trail
p2engine ledger audit
p2engine ledger audit --type wallet_created
p2engine ledger audit --type transfer_executed --limit 100
```

## 3. **Agent Chat Interactions**

### Basic Agent Interactions

```bash
# Start chat with any agent
p2engine chat with agent_alpha
```

In the chat, try these commands:

**Balance Checking:**

```
Check my balance
What's my current balance?
How much money do I have?
Check the balance of agent_beta
What's treasurer's balance?
```

**Fund Transfers:**

```
Transfer 20 to agent_beta for helping me
Send 15 units to agent_helper as payment
Give treasurer 30 units for management
Transfer 50 to child with reason "education fund"
```

**Transaction History:**

```
Show my transaction history
What transfers have I made?
Show my recent transactions
List my last 5 transactions
```

### Advanced Multi-Agent Scenarios

#### Scenario 1: Delegation with Rewards

```bash
p2engine chat with agent_alpha
```

```
Check my balance
Delegate to agent_helper: What's the weather in Paris?
If they did a good job, reward agent_helper with 20 units
Check my balance again
Show my transaction history
```

#### Scenario 2: Treasury Management

```bash
p2engine chat with treasurer
```

```
Check my balance
Check the balance of all agents: agent_alpha, agent_beta, agent_helper
Transfer 50 to agent_alpha for operations
Transfer 30 to agent_beta for development
Transfer 20 to agent_helper for support
Show my transaction history
Check system metrics
```

#### Scenario 3: Complex Delegation Chain

```bash
p2engine chat with agent_alpha
```

```
Check my balance
Delegate to treasurer: Please distribute 100 units equally among agent_beta, agent_helper, and child
Check my balance after delegation
Show all recent transactions
```

## 4. **Testing Scenarios via Shell**

```bash
p2engine shell
```

### Interactive Testing Session

```
# Create multiple conversations
chat with agent_alpha
> Check balance
> Transfer 25 to agent_beta
> exit

chat with agent_beta
> Check balance
> Thank agent_alpha for the funds by sending back 5 units
> exit

# View all conversations
conversation list

# Inspect specific conversation
conversation stack <conversation_name> --n 20

# Check ledger state
ledger metrics
```

### Parallel Agent Testing

```
# Terminal 1 - Watch the stack
p2engine conversation watch <conversation_name>

# Terminal 2 - Interact
p2engine chat resume <conversation_name>
```

## 5. **Rollout Testing for Ledger**

Create `test_ledger_scenarios.yml`:

```yaml
teams:
  basic_ledger_test:
    initial_message: |
      1. Check my balance
      2. Transfer 30 to agent_helper with reason "test payment"
      3. Check my balance again
      4. Show my transaction history
    base:
      agent_id: agent_alpha
      tools: ["check_balance", "transfer_funds", "transaction_history"]
    variants:
      - id: baseline
        model: openai/gpt-4o

  reward_test:
    initial_message: |
      Delegate to agent_helper: analyze the weather in Tokyo.
      After they respond, reward them 25 units if they did well.
    base:
      agent_id: agent_alpha
      tools: ["delegate", "reward_agent", "check_balance"]
    variants:
      - id: generous
        initial_message: |
          Ask agent_helper for weather info, then reward them 50 units
      - id: moderate
        initial_message: |
          Ask agent_helper for weather info, then reward them 20 units

  treasury_distribution:
    initial_message: |
      Check balances of agent_alpha, agent_beta, and agent_helper.
      Ensure each has at least 80 units by transferring from my account.
      Show the transaction history after.
    base:
      agent_id: treasurer
      tools: ["check_balance", "transfer_funds", "transaction_history"]
    variants:
      - id: equalizer
        initial_message: |
          Give each agent exactly 100 units total
      - id: proportional
        initial_message: |
          Give agents funds proportional to their current balance
```

Run it:

```bash
p2engine rollout start test_ledger_scenarios.yml --follow
```

## 6. **Error Testing & Edge Cases**

### Test Error Handling

```
# Insufficient funds
Transfer 1000 to agent_beta  # Should fail gracefully

# Invalid amounts
Transfer -50 to agent_beta   # Should reject
Transfer 0 to agent_beta     # Should reject

# Non-existent agents
Transfer 50 to agent_xyz     # Should handle gracefully
Check balance of fake_agent  # Should show error
```

### Test Concurrent Operations

```bash
# Terminal 1
p2engine chat with agent_alpha
> Transfer 50 to agent_beta

# Terminal 2 (simultaneously)
p2engine chat with agent_beta
> Transfer 30 to agent_alpha
```

## 7. **Monitoring & Verification**

### Real-time Monitoring

```bash
# Watch ledger events as they happen
p2engine artifact show ledger:p2engine_default --tag transfer_executed --limit 20

# Monitor specific conversation
p2engine conversation watch <conv_name> --interval 1

# Check audit trail
p2engine ledger audit --since "2024-01-01T00:00:00Z"
```

### Verification Commands

```bash
# After complex operations
p2engine ledger metrics  # Total should remain constant
p2engine ledger audit --type transfer_executed --limit 50

# Verify specific agent state
p2engine ledger balance <agent_id>
p2engine ledger history <agent_id>
```

## 8. **Advanced Tool Combinations**

### Weather + Payment Flow

```
What's the weather in Paris?
If it's sunny, send 20 units to agent_helper for vacation fund
If it's rainy, send 10 units to agent_helper for umbrella fund
```

### Conditional Rewards

```
Delegate to child: Solve this math problem: 15 * 7
If they get it right, reward them 10 units
Check both our balances after
```

### Multi-hop Delegation

```
Ask treasurer to ask agent_beta to check agent_helper's balance
If agent_helper has less than 50, ask treasurer to fund them
```

## Example Full Test Session

```bash
# 1. Initialize
p2engine ledger init --balance 150

# 2. Start main agent
p2engine chat with agent_alpha

# In chat:
Check my balance
Show me the weather in Tokyo
Transfer 25 to agent_helper for weather services
Delegate to treasurer: Please ensure all agents have at least 100 units
Check my balance
Show my recent transactions
Ask agent_helper to thank me if they received the payment
exit

# 3. Verify results
p2engine ledger metrics
p2engine ledger audit --limit 20
p2engine conversation stack <conv_name> --n 30
```

This comprehensive testing suite will help you verify that all ledger operations work correctly through both CLI commands and agent interactions!
