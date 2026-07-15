import asyncio
import logging
from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger("gateway")

# Initialize the asynchronous OpenAI client pointing to Ollama
# We use AsyncOpenAI so that the web server doesn't freeze while waiting for network responses.
client = AsyncOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY
)

async def stream_llm_response(user_message: str) -> AsyncGenerator[str, None]:
    """
    Calls Ollama and streams the response back token by token.
    Requirement 4: Enforces a strict timeout and yields a graceful fallback if it fails.
    """
    fallback_message = "🤖 System: I'm having trouble generating a response right now. Please try again in a moment!"
    
    try:
        # We wrap the network call inside asyncio.wait_for to set a strict stopwatch.
        # If Ollama takes longer than 5 seconds to initiate the stream, it raises a TimeoutError.
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": user_message}],
                stream=True # Tells Ollama to stream back word-by-word
            ),
            timeout=5.0 # 5-second timeout guard
        )

        # Iterate over the words as they stream in from Ollama
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    except asyncio.TimeoutError:
        # REQUIREMENT 4: The model hung! Log it and stream the polite fallback message instead.
        logger.error("❌ LLM request timed out after 5 seconds.")
        yield fallback_message

    except Exception as e:
        # REQUIREMENT 4: The model errored out (e.g., Ollama is turned off).
        # Log the raw stack trace privately on our server, but keep the user interface clean.
        logger.error(f"❌ LLM communication error: {str(e)}")
        yield fallback_message