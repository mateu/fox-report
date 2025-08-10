from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings

# Load variables from .env before creating settings so BaseSettings can see them
load_dotenv()


class Settings(BaseSettings):
    smtp_host: str = Field("smtp.gmail.com", env="SMTP_HOST")
    smtp_user: str = Field("", env="SMTP_USER")
    smtp_pass: str = Field("", env=["SMTP_PASS", "GMAIL_APP_PASSWORD"])
    tz_local: str = "America/Denver"  # Mountain Time
    # SQLAlchemy database URL. Defaults to local Frigate SQLite DB.
    # Example: "sqlite:////home/hunter/frigate/config/frigate.db"
    db_url: str = Field(
        "sqlite:////home/hunter/frigate/config/frigate.db",
        env="DB_URL",
    )

    @computed_field(return_type=ZoneInfo)
    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.tz_local)


settings = Settings()  # import-time singleton
