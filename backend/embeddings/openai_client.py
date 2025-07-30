#backend/embeddings/openai
import os
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

DEPLOY = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")  # Ej: "text-embedding-ada-002"
