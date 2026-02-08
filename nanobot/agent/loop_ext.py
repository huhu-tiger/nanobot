"""Agent loop extensions for cron tools and channel context."""

from typing import TYPE_CHECKING
import re

from loguru import logger

if TYPE_CHECKING:
    from nanobot.agent.tools.registry import ToolRegistry
    from nanobot.cron.service import CronService


def register_cron_tools(tools: "ToolRegistry", cron_service: "CronService") -> None:
    """
    Register cron management tools.
    
    Args:
        tools: Tool registry
        cron_service: Cron service instance
    """
    from nanobot.agent.tools.cron import (
        CreateCronJobTool,
        ListCronJobsTool,
        DeleteCronJobTool,
        ToggleCronJobTool,
    )
    
    tools.register(CreateCronJobTool(cron_service))
    tools.register(ListCronJobsTool(cron_service))
    tools.register(DeleteCronJobTool(cron_service))
    tools.register(ToggleCronJobTool(cron_service))
    
    logger.info("Registered cron tools: create_cron_job, list_cron_jobs, delete_cron_job, toggle_cron_job")


def build_channel_info(msg) -> dict[str, str]:
    """
    Extract channel info from inbound message.
    
    Args:
        msg: InboundMessage instance
    
    Returns:
        Dict with channel, chat_id, sender_id
    """
    return {
        "channel": msg.channel,
        "chat_id": msg.chat_id,
        "sender_id": msg.sender_id,
    }


def should_use_cron_tool(message: str) -> bool:
    """
    Check if the message is requesting a reminder/scheduled task.
    
    Args:
        message: User message
    
    Returns:
        True if message is requesting a reminder
    """
    # 提醒相关的关键词
    reminder_keywords = [
        r'提醒',
        r'提示',
        r'定时',
        r'闹钟',
        r'alarm',
        r'remind',
        r'schedule',
        r'cron',
        r'每天.*点',
        r'明天.*点',
        r'下午.*点',
        r'早上.*点',
        r'晚上.*点',
        r'\d+点\d*分',
        r'\d+:\d+',
    ]
    
    message_lower = message.lower()
    
    for pattern in reminder_keywords:
        if re.search(pattern, message_lower):
            return True
    
    return False


def create_tool_reminder_message(user_message: str, channel: str, recipient: str) -> str:
    """
    Create a system message to remind LLM to use the tool.
    
    Args:
        user_message: Original user message
        channel: Channel name
        recipient: Recipient ID
    
    Returns:
        System reminder message
    """
    return f"""⚠️ SYSTEM REMINDER ⚠️

The user just requested: "{user_message}"

This is a reminder/scheduled task request. You MUST call the create_cron_job tool!

DO NOT just reply with text. Call the tool with:
- deliver=true
- channel="{channel}"
- recipient="{recipient}"

Example:
{{
  "name": "create_cron_job",
  "arguments": {{
    "name": "提醒任务",
    "message": "💧 提醒：该喝水啦！",
    "schedule_type": "at",
    "timestamp": <calculate>,
    "deliver": true,
    "channel": "{channel}",
    "recipient": "{recipient}"
  }}
}}"""
