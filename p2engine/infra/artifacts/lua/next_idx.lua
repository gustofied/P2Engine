-- infra/artifacts/lua/next_idx.lua
-- Atomic helper for p2engine Phase-1 header upgrade.
--
-- ARGV[1] = session_id
-- ARGV[2] = branch_id
-- ARGV[3] = ref  (artifact reference / UUID hex)

local counter_key = "artifacts:" .. ARGV[1] .. ":branch:" .. ARGV[2] .. ":step_idx"
local idx = redis.call("INCR", counter_key) - 1          -- convert to 0-based

-- NEW: safety-TTL so stray counters don’t linger
redis.call("PEXPIRE", counter_key, 86400000)   -- 24 h

local branch_z = "artifacts:" .. ARGV[1] .. ":branch:" .. ARGV[2]
redis.call("ZADD", branch_z, idx, ARGV[3])

return idx
