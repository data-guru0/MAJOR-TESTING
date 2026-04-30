from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    github_webhook_secret: str = ""

    class Config:
        env_file = ".env"
