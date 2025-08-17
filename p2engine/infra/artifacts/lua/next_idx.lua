local counter_key = "artifacts:" .. ARGV[1] .. ":branch:" .. ARGV[2] .. ":step_idx"
local idx = redis.call("INCR", counter_key) - 1         


redis.call("PEXPIRE", counter_key, 86400000)  

local branch_z = "artifacts:" .. ARGV[1] .. ":branch:" .. ARGV[2]
redis.call("ZADD", branch_z, idx, ARGV[3])

return idx
