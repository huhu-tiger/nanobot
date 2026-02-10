---
name: cron
description: Schedule reminders and recurring tasks.
---

# Cron

**IMPORTANT**: When user asks to set a reminder or schedule a task, you MUST call the `cron` tool. Do NOT just say you've created it - actually call the tool!

Use the `cron` tool to schedule reminders or recurring tasks.

## Two Modes

1. **Reminder** - message is sent directly to user
2. **Task** - message is a task description, agent executes and sends result

## Examples

Fixed reminder (5 minutes from now):
```
cron(action="add", message="📅 提醒：该开会啦！", at_timestamp=<current_time + 300>)
```

Recurring reminder:
```
cron(action="add", message="Time to take a break!", every_seconds=1200)
```

Dynamic task (agent executes each time):
```
cron(action="add", message="Check HKUDS/nanobot GitHub stars and report", every_seconds=600)
```

List/remove:
```
cron(action="list")
cron(action="remove", job_id="abc123")
```

## Time Expressions

| User says | Parameters |
|-----------|------------|
| 5分钟后提醒我 | at_timestamp: current_time + 300 |
| every 20 minutes | every_seconds: 1200 |
| every hour | every_seconds: 3600 |
| every day at 8am | cron_expr: "0 8 * * *" |
| weekdays at 5pm | cron_expr: "0 17 * * 1-5" |

## Critical Rules

1. **ALWAYS call the tool** - Never pretend to create a reminder without calling `cron`
2. **Use at_timestamp for one-time reminders** - Calculate: current_timestamp + seconds_delay
3. **Confirm after creation** - After calling the tool, confirm the job ID and next run time
