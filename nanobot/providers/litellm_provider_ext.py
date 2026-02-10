"""Extended LiteLLM provider with logging support."""

from typing import Any

from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.providers.base import LLMResponse
from nanobot.utils.logging import log_llm_request, log_llm_response, log_llm_error


class LiteLLMProviderExt(LiteLLMProvider):
    """Extended LiteLLM provider with comprehensive logging."""
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request with logging.
        
        This method wraps the parent chat() method with request/response logging.
        """
        resolved_model = self._resolve_model(model or self.default_model)
        
        # Log request
        log_llm_request(
            model=resolved_model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            api_base=self.api_base,
            depth=2
        )
        
        try:
            # Call parent implementation
            response = await super().chat(
                messages=messages,
                tools=tools,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Log response
            log_llm_response(
                content=response.content,
                tool_calls=response.tool_calls,
                finish_reason=response.finish_reason,
                usage=response.usage,
                depth=2
            )
            
            return response
            
        except Exception as e:
            # Log error
            log_llm_error(error=e, depth=2)
            raise
