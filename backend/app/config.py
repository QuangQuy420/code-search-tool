from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "code-search-tool"
    GROQ_API_KEY: str = ""
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "https://localhost:3000",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_parse_none_str": "null",
        "env_ignore_empty": True,
    }


settings = Settings()
