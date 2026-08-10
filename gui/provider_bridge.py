"""
Bridge layer between synchronous Tkinter GUI and asynchronous CustomProvider.

Design:
- asyncio event loop runs in a separate daemon thread (not in Tkinter main thread)
- Tkinter main thread communicates with async thread via thread-safe mechanisms
- Provider instances are cached by (api_key, api_base, model) tuple
- Callbacks: on_chunk(text), on_complete(usage_dict), on_error(error_msg)
"""

from __future__ import annotations

import asyncio
import threading
from typing import Callable, Any, Dict, Optional, Tuple
from dataclasses import dataclass
from queue import Queue, Empty

from providers.custom_provider import CustomProvider
from providers.base import LLMResponse, ToolCallRequest


@dataclass
class _Request:
    """Internal request object for queue-based communication."""
    messages: list[dict[str, Any]]
    model: str | None
    max_tokens: int
    temperature: float
    reasoning_effort: str | None
    tool_choice: str | dict[str, Any] | None
    tools: list[dict[str, Any]] | None
    on_chunk: Callable[[str], None] | None
    on_complete: Callable[[Dict[str, int]], None] | None
    on_error: Callable[[str], None] | None
    stream: bool
    response_queue: Queue | None  # For sync mode


class ProviderBridge:
    """
    Bridge between synchronous Tkinter GUI and asynchronous CustomProvider.
    
    Features:
    - Runs asyncio event loop in a separate daemon thread
    - Caches CustomProvider instances by (api_key, api_base, model)
    - Provides chat() (non-streaming) and stream_chat() (streaming) interfaces
    - Uses callback pattern: on_chunk, on_complete, on_error
    - Graceful shutdown via shutdown() method
    
    Usage:
    
        bridge = ProviderBridge(api_key="sk-...", api_base="https://api.openai.com/v1")
        bridge.start()
        
        # Non-streaming (callback mode)
        def on_complete(usage):
            print(f"Done: {usage}")
        def on_error(err):
            print(f"Error: {err}")
        
        bridge.chat(
            messages=[{"role": "user", "content": "Hello"}],
            on_complete=on_complete,
            on_error=on_error
        )
        
        # Streaming (callback mode)
        def on_chunk(text):
            print(text, end="", flush=True)
        
        bridge.stream_chat(
            messages=[{"role": "user", "content": "Hello"}],
            on_chunk=on_chunk,
            on_complete=on_complete,
            on_error=on_error
        )
        
        # Shutdown when done
        bridge.shutdown()
    """
    
    def __init__(self, api_key: str = "no-key", api_base: str = "http://localhost:8000/v1"):
        """
        Initialize ProviderBridge.
        
        Args:
            api_key: API key for LLM provider (default: "no-key")
            api_base: Base URL for LLM provider API (default: "http://localhost:8000/v1")
        """
        self._api_key = api_key
        self._api_base = api_base
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._request_queue: Queue[_Request] = Queue()
        self._stop_event = threading.Event()
        self._providers: Dict[Tuple[str, str, str], CustomProvider] = {}
        self._lock = threading.Lock()
        self._loop_ready = threading.Event()
        
    def start(self):
        """
        Start the background thread with asyncio event loop.
        
        This method spawns a daemon thread that runs the asyncio event loop
        and processes chat requests from the queue.
        """
        if self._thread and self._thread.is_alive():
            return
            
        def _run_loop():
            """Run asyncio event loop in background thread."""
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop_ready.set()
            
            # Schedule a periodic checker to process requests from queue
            def _check_queue():
                if self._stop_event.is_set():
                    self._loop.stop()
                    return
                try:
                    while True:
                        try:
                            request = self._request_queue.get_nowait()
                            # Submit coroutine to event loop
                            asyncio.ensure_future(
                                self._process_request(request),
                                loop=self._loop
                            )
                        except Empty:
                            break
                except Exception as e:
                    print(f"Error in ProviderBridge queue check: {e}")
                # Schedule next check
                self._loop.call_later(0.1, _check_queue)
            
            # Start the first check
            self._loop.call_soon(_check_queue)
            
            # Run event loop forever (until stopped)
            self._loop.run_forever()
            
            # Cleanup: close all provider clients
            try:
                if self._loop and not self._loop.is_closed():
                    self._loop.run_until_complete(self._cleanup_providers())
            except Exception as e:
                print(f"Error during cleanup: {e}")
            
            if self._loop and not self._loop.is_closed():
                self._loop.close()
            self._loop = None
            
        self._thread = threading.Thread(
            target=_run_loop,
            daemon=True,
            name="ProviderBridge-AsyncLoop"
        )
        self._thread.start()
        self._loop_ready.wait(timeout=5)  # Wait for loop to be ready
        
    async def _cleanup_providers(self):
        """Cleanup all cached provider instances."""
        for key, provider in self._providers.items():
            try:
                await provider._client.close()
            except Exception as e:
                print(f"Error closing provider client {key}: {e}")
        self._providers.clear()
        
    def _get_provider(self, model: str) -> CustomProvider:
        """
        Get or create a cached CustomProvider instance.
        
        Args:
            model: Model name (used as default_model)
            
        Returns:
            Cached or newly created CustomProvider instance
        """
        key = (self._api_key, self._api_base, model)
        with self._lock:
            if key not in self._providers:
                self._providers[key] = CustomProvider(
                    api_key=self._api_key,
                    api_base=self._api_base,
                    default_model=model,
                )
            return self._providers[key]
    
    async def _process_request(self, request: _Request):
        """
        Process a chat request asynchronously.
        
        Args:
            request: _Request object containing messages, callbacks, etc.
        """
        try:
            if request.stream:
                await self._process_streaming(request)
            else:
                await self._process_non_streaming(request)
        except Exception as e:
            error_msg = f"ProviderBridge error: {e}"
            print(error_msg)
            if request.on_error:
                try:
                    request.on_error(error_msg)
                except Exception as callback_error:
                    print(f"Error in on_error callback: {callback_error}")
            elif request.response_queue:
                request.response_queue.put(
                    LLMResponse(content=error_msg, finish_reason="error")
                )
    
    async def _process_non_streaming(self, request: _Request):
        """Process non-streaming chat request."""
        # Get or create provider (cached by api_key+api_base+model)
        provider = self._get_provider(request.model or "default")
        
        # Call provider's chat method
        response = await provider.chat(
            messages=request.messages,
            tools=request.tools,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            reasoning_effort=request.reasoning_effort,
            tool_choice=request.tool_choice,
        )
        
        # Handle response
        if response.finish_reason == "error":
            error_msg = response.content or "Unknown error"
            if request.on_error:
                request.on_error(error_msg)
            elif request.response_queue:
                request.response_queue.put(response)
        else:
            # If there's content and on_chunk is provided, call it first
            if request.on_chunk and response.content:
                request.on_chunk(response.content)
            
            # Then call on_complete callback with usage dict
            if request.on_complete:
                request.on_complete(response.usage)
            
            # For sync mode, put full response in queue
            if request.response_queue:
                request.response_queue.put(response)
    
    async def _process_streaming(self, request: _Request):
        """
        Process streaming chat request.
        
        Note: CustomProvider.chat() doesn't support streaming natively.
        This implementation uses the underlying OpenAI client directly with stream=True.
        """
        # Get or create provider (cached by api_key+api_base+model)
        provider = self._get_provider(request.model or "default")
        
        # Prepare kwargs for OpenAI API
        kwargs: dict[str, Any] = {
            "model": request.model or provider.default_model,
            "messages": provider._sanitize_empty_content(request.messages),
            "max_tokens": max(1, request.max_tokens),
            "temperature": request.temperature,
            "stream": True,
        }
        if request.reasoning_effort:
            kwargs["reasoning_effort"] = request.reasoning_effort
        if request.tools:
            kwargs.update(tools=request.tools, tool_choice=request.tool_choice or "auto")
        
        try:
            # Use streaming API
            stream = await provider._client.chat.completions.create(**kwargs)
            
            full_content = []
            usage = {}
            
            async for chunk in stream:
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # Extract content from chunk
                if delta.content:
                    content_piece = delta.content
                    full_content.append(content_piece)
                    
                    # Call on_chunk callback
                    if request.on_chunk:
                        try:
                            request.on_chunk(content_piece)
                        except Exception as callback_error:
                            print(f"Error in on_chunk callback: {callback_error}")
                
                # Extract usage from final chunk (some providers include it)
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }
            
            # Call on_complete with usage
            if request.on_complete:
                try:
                    request.on_complete(usage)
                except Exception as callback_error:
                    print(f"Error in on_complete callback: {callback_error}")
                    
        except Exception as e:
            error_msg = f"Streaming error: {e}"
            print(error_msg)
            if request.on_error:
                try:
                    request.on_error(error_msg)
                except Exception as callback_error:
                    print(f"Error in on_error callback: {callback_error}")
            else:
                raise
    
    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        on_complete: Callable[[Dict[str, int]], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_chunk: Callable[[str], None] | None = None,
    ) -> LLMResponse | None:
        """
        Non-streaming chat interface.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (optional, uses provider default)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            reasoning_effort: Reasoning effort level (optional)
            tool_choice: Tool selection strategy (optional)
            tools: List of tool definitions (optional)
            on_complete: Callback with usage dict (optional)
            on_error: Callback with error message (optional)
            on_chunk: Callback with content (optional, for compatibility)
            
        Returns:
            LLMResponse if no callbacks provided (synchronous mode),
            None if callbacks provided (asynchronous mode)
            
        Note:
            - If callbacks are provided, runs asynchronously and returns None
            - If no callbacks provided, blocks until response and returns LLMResponse
        """
        if on_complete or on_error or on_chunk:
            # Async mode: use callbacks
            request = _Request(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                tool_choice=tool_choice,
                tools=tools,
                on_chunk=on_chunk,
                on_complete=on_complete,
                on_error=on_error,
                stream=False,
                response_queue=None,
            )
            self._request_queue.put(request)
            return None
        else:
            # Sync mode: block until response
            response_queue: Queue = Queue()
            request = _Request(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                tool_choice=tool_choice,
                tools=tools,
                on_chunk=None,
                on_complete=None,
                on_error=None,
                stream=False,
                response_queue=response_queue,
            )
            self._request_queue.put(request)
            
            # Wait for response (with timeout)
            try:
                response = response_queue.get(timeout=120)  # 2 min timeout
                return response
            except Empty:
                return LLMResponse(
                    content="Error: Request timeout (120s)",
                    finish_reason="error"
                )
    
    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_complete: Callable[[Dict[str, int]], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        """
        Streaming chat interface.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (optional, uses provider default)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            reasoning_effort: Reasoning effort level (optional)
            tool_choice: Tool selection strategy (optional)
            tools: List of tool definitions (optional)
            on_chunk: Callback with text chunk (recommended for streaming)
            on_complete: Callback with usage dict (optional)
            on_error: Callback with error message (optional)
            
        Note:
            - This method always runs asynchronously (returns immediately)
            - on_chunk callback will be called for each text chunk
            - on_complete callback will be called when streaming finishes
            - on_error callback will be called if an error occurs
        """
        request = _Request(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            tool_choice=tool_choice,
            tools=tools,
            on_chunk=on_chunk,
            on_complete=on_complete,
            on_error=on_error,
            stream=True,
            response_queue=None,
        )
        self._request_queue.put(request)
    
    def shutdown(self, timeout: float = 5.0):
        """
        Graceful shutdown: stop the event loop and clean up resources.
        
        Args:
            timeout: Maximum seconds to wait for thread to finish
        """
        self._stop_event.set()
        
        # Stop the event loop from the main thread
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            
        self._thread = None
        self._loop = None
        
        # Clear provider cache
        with self._lock:
            self._providers.clear()
    
    def is_running(self) -> bool:
        """Check if the background thread is running."""
        return self._thread is not None and self._thread.is_alive()
    
    def update_config(self, api_key: str | None = None, api_base: str | None = None):
        """
        Update API configuration.
        
        Args:
            api_key: New API key (optional)
            api_base: New API base URL (optional)
            
        Note:
            - This will clear the provider cache, so new providers will be
              created with the updated config on next chat request
        """
        if api_key is not None:
            self._api_key = api_key
        if api_base is not None:
            self._api_base = api_base
        
        # Clear provider cache to force recreation with new config
        with self._lock:
            self._providers.clear()


# Convenience function for testing
def test_provider_bridge():
    """Test function to verify ProviderBridge works correctly."""
    import time
    
    print("Testing ProviderBridge...")
    
    bridge = ProviderBridge(
        api_key="no-key",
        api_base="http://localhost:8000/v1"
    )
    bridge.start()
    
    print(f"Bridge running: {bridge.is_running()}")
    
    # Test non-streaming with callbacks
    print("\n1. Testing non-streaming chat with callbacks...")
    response_received = threading.Event()
    response_usage = None
    
    def on_complete(usage):
        global response_usage
        response_usage = usage
        print(f"   on_complete called with usage: {usage}")
        response_received.set()
    
    def on_error(err):
        print(f"   on_error called: {err}")
        response_received.set()
    
    bridge.chat(
        messages=[{"role": "user", "content": "Say 'test passed' in Chinese"}],
        model="default",
        on_complete=on_complete,
        on_error=on_error,
    )
    
    # Wait for response
    if response_received.wait(timeout=30):
        print("   Non-streaming test passed!")
    else:
        print("   Non-streaming test timed out!")
    
    # Test streaming with callbacks
    print("\n2. Testing streaming chat with callbacks...")
    chunks_received = []
    streaming_done = threading.Event()
    
    def on_chunk(text):
        chunks_received.append(text)
        print(f"  _chunk: {text}")
    
    def on_complete_stream(usage):
        print(f"   Streaming complete. Usage: {usage}")
        streaming_done.set()
    
    def on_error_stream(err):
        print(f"   Streaming error: {err}")
        streaming_done.set()
    
    bridge.stream_chat(
        messages=[{"role": "user", "content": "Count from 1 to 5"}],
        model="default",
        on_chunk=on_chunk,
        on_complete=on_complete_stream,
        on_error=on_error_stream,
    )
    
    # Wait for streaming to finish
    if streaming_done.wait(timeout=30):
        print(f"   Streaming test passed! Received {len(chunks_received)} chunks.")
    else:
        print("   Streaming test timed out!")
    
    # Test sync mode (no callbacks)
    print("\n3. Testing synchronous chat (no callbacks)...")
    try:
        response = bridge.chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="default",
        )
        if response:
            print(f"   Sync response: {response.content}")
            print("   Sync test passed!")
        else:
            print("   Sync test failed: no response!")
    except Exception as e:
        print(f"   Sync test error: {e}")
    
    # Shutdown
    print("\n4. Shutting down...")
    bridge.shutdown()
    print(f"   Bridge running after shutdown: {bridge.is_running()}")
    print("\nAll tests completed.")


if __name__ == "__main__":
    test_provider_bridge()
