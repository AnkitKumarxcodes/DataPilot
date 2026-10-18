import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openrouter import ChatOpenRouter


def pick_llm(level: str):
    """Return a free-tier chat model suited to the requested capability level.

    Each provider reads its API key from the matching environment variable.
    """
    load_dotenv()
    normalized_level = level.lower()

    if normalized_level == "low":
        return ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite",
            google_api_key=os.environ["GOOGLE_API_KEY"],
        )
    elif normalized_level == "medium":
        return ChatGroq(
            model="openai/gpt-oss-20b",
            api_key=os.environ["GROQ_API_KEY"],
        )
    elif normalized_level == "high":
        return ChatOpenRouter(
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    else:
        raise ValueError("Invalid level specified. Choose from 'low', 'medium', or 'high'.")

