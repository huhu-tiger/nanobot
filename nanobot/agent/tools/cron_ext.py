"""Extended Cron tool with at_timestamp support."""

from typing import Any

from nanobot.agent.tools.cron import CronTool
from nanobot.cron.types import CronSchedule


class CronToolExt(CronTool):
    """Extended CronTool with support for one-time reminders using at_timestamp."""
    
    @property
    def description(self) -> str:
        return "⚠️ CRITICAL: MUST call this tool for reminders! Schedule reminders and recurring tasks. Actions: add, list, remove."
    
    @property
    def parameters(self) -> dict[str, Any]:
        """Extended parameters including at_timestamp and name."""
        base_params = super().parameters
        # Add at_timestamp and name parameters
        base_params["properties"]["at_timestamp"] = {
            "type": "integer",
            "description": "Unix timestamp in seconds for one-time reminder (for add)"
        }
        base_params["properties"]["name"] = {
            "type": "string",
            "description": "Job name (for add)"
        }
        return base_params
    
    async def execute(
        self,
        action: str,
        name: str = "",
        message: str = "",
        at_timestamp: int | None = None,
        every_seconds: int | None = None,
        cron_expr: str | None = None,
        job_id: str | None = None,
        **kwargs: Any
    ) -> str:
        """Execute with support for at_timestamp parameter."""
        if action == "add":
            return self._add_job_ext(name, message, at_timestamp, every_seconds, cron_expr)
        # Delegate other actions to parent
        return await super().execute(action, message, every_seconds, cron_expr, job_id, **kwargs)
    
    def _add_job_ext(
        self, 
        name: str, 
        message: str, 
        at_timestamp: int | None, 
        every_seconds: int | None, 
        cron_expr: str | None
    ) -> str:
        """Add job with at_timestamp support."""
        if not message:
            return "Error: message is required for add"
        if not self._channel or not self._chat_id:
            return "Error: no session context (channel/chat_id)"
        
        # Build schedule
        if at_timestamp:
            # One-time reminder at specific timestamp
            schedule = CronSchedule(kind="at", at_ms=at_timestamp * 1000)
        elif every_seconds:
            # Recurring reminder
            schedule = CronSchedule(kind="every", every_ms=every_seconds * 1000)
        elif cron_expr:
            # Cron expression
            schedule = CronSchedule(kind="cron", expr=cron_expr)
        else:
            return "Error: one of at_timestamp, every_seconds, or cron_expr is required"
        
        # Use provided name or generate from message
        job_name = name if name else message[:30]
        
        job = self._cron.add_job(
            name=job_name,
            schedule=schedule,
            message=message,
            deliver=True,
            channel=self._channel,
            to=self._chat_id,
        )
        
        # Format next run time
        import time
        next_run = ""
        if job.state.next_run_at_ms:
            next_run = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(job.state.next_run_at_ms / 1000))
        
        return f"✅ Created job '{job.name}' (ID: {job.id})\nNext run: {next_run}"
