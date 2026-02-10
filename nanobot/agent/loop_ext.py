"""Agent loop extensions for cron tools and channel context."""

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from nanobot.agent.tools.registry import ToolRegistry
    from nanobot.cron.service import CronService


def register_cron_tools(tools: "ToolRegistry", cron_service: "CronService") -> None:
    """
    Register cron management tool.
    
    Args:
        tools: Tool registry
        cron_service: Cron service instance
    """
    from nanobot.agent.tools.cron_ext import CronToolExt
    
    tools.register(CronToolExt(cron_service))
    
    logger.info("Registered extended cron tool")
