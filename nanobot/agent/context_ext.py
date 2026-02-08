"""Context builder extensions for channel-aware prompts."""

from typing import Any


def build_channel_context_section(channel_info: dict[str, str]) -> str:
    """
    Build channel context section for system prompt.
    
    Args:
        channel_info: Dict with channel, chat_id, sender_id
    
    Returns:
        Formatted channel context section
    """
    channel = channel_info.get("channel", "unknown")
    chat_id = channel_info.get("chat_id", "unknown")
    sender_id = channel_info.get("sender_id", "unknown")
    
    return f"""

## Current Channel Context
You are currently chatting with a user through: **{channel}**
- Channel: {channel}
- Chat ID: {chat_id}
- User ID: {sender_id}

⚠️ ⚠️ ⚠️ CRITICAL INSTRUCTION FOR REMINDERS AND SCHEDULED TASKS ⚠️ ⚠️ ⚠️

When the user asks you to create a reminder or scheduled task (例如："提醒我喝水", "下午3点提醒", "明天早上9点提醒我"), 
you MUST use the create_cron_job tool with these EXACT parameters:

REQUIRED PARAMETERS:
- deliver=true (必须设置为 true，这样消息会直接发送到用户)
- channel="{channel}" (当前频道)
- recipient="{sender_id}" (当前用户 ID)
- message="💧 提醒：该喝水啦！" (或其他提醒内容)

DO NOT just reply with text like "提醒已设置". You MUST call the create_cron_job tool!

Example tool call for "下午三点45分提醒喝水":
{{
  "name": "create_cron_job",
  "arguments": {{
    "name": "喝水提醒15:45",
    "message": "💧 提醒：该喝水啦！",
    "schedule_type": "at",
    "timestamp": <calculate based on current time>,
    "deliver": true,
    "channel": "{channel}",
    "recipient": "{sender_id}"
  }}
}}
"""


def inject_channel_info(
    system_prompt: str,
    channel_info: dict[str, str] | None
) -> str:
    """
    Inject channel context into system prompt.
    
    Args:
        system_prompt: Original system prompt
        channel_info: Optional channel context
    
    Returns:
        System prompt with channel context injected
    """
    if not channel_info:
        return system_prompt
    
    # Find the workspace section and inject after it
    channel_section = build_channel_context_section(channel_info)
    
    # Insert before "IMPORTANT:" section
    if "IMPORTANT:" in system_prompt:
        parts = system_prompt.split("IMPORTANT:", 1)
        return parts[0] + channel_section + "\n\nIMPORTANT:" + parts[1]
    
    # Fallback: append at the end
    return system_prompt + channel_section
