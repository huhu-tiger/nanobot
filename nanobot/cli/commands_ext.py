"""CLI commands extensions for cron callback."""

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from nanobot.bus.queue import MessageBus
    from nanobot.agent.loop import AgentLoop
    from nanobot.cron.types import CronJob


def create_cron_callback(bus: "MessageBus", agent: "AgentLoop"):
    """
    Create cron job callback that handles both direct delivery and agent processing.
    
    Args:
        bus: Message bus for sending messages
        agent: Agent loop for processing messages
    
    Returns:
        Async callback function
    """
    async def on_cron_job(job: "CronJob") -> str | None:
        """Execute a cron job - prioritize direct message delivery."""
        from nanobot.bus.events import OutboundMessage
        
        # If deliver flag is set, send message directly to channel first
        if job.payload.deliver and job.payload.to:
            logger.info(f"Cron: delivering message directly to {job.payload.channel}:{job.payload.to}")
            
            # Send message directly without agent processing
            await bus.publish_outbound(OutboundMessage(
                channel=job.payload.channel or "feishu",
                chat_id=job.payload.to,
                content=job.payload.message
            ))
            
            return job.payload.message
        else:
            # No deliver flag - process through agent (for complex tasks)
            logger.info(f"Cron: processing message through agent")
            response = await agent.process_direct(
                job.payload.message,
                session_key=f"cron:{job.id}"
            )
            return response
    
    return on_cron_job
