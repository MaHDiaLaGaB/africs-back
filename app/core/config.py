from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # API related settings
    API_V1_STR: str = Field("/api", description="API prefix for version 1")
    ENV: str = Field(
        "dev", description="Application environment (dev, staging, production)"
    )

    # Supabase settings
    DATABASE_URI: str = Field(..., description="Database URI for SQLAlchemy")

    # Server settings
    SERVER_PORT: int = Field(6699, description="Port on which the server runs")

    # General settings
    PROJECT_NAME: str = Field("Wasata", description="Name of the project")

    # Sentry settings
    SENTRY_DSN: Optional[str] = Field(None, description="DSN for Sentry error tracking")

    # LLM settings
    # OPENAI_API_KEY: str = Field(..., description="API key for OpenAI")

    class ConfigDict:
        case_sensitive = True
        env_file = ".env"
        json_encoders = {SecretStr: lambda v: v.get_secret_value() if v else None}

    @field_validator(
        "DATABASE_URI",
    )
    @classmethod
    def not_empty(cls, v, field):
        if isinstance(v, SecretStr):
            if not v.get_secret_value():
                raise ValueError(f"{field.name} cannot be empty")
        else:
            if not v:
                raise ValueError(f"{field.name} cannot be empty")
        return v


# Initialize the settings
settings = Settings()
