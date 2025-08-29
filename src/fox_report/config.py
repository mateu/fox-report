from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings

# Load variables from .env before creating settings so BaseSettings can see them
load_dotenv()


class Settings(BaseSettings):
    # Email Configuration
    email_sender: str = Field(
        "sender@example.com", alias="EMAIL_SENDER"
    )  # SMTP username/from address
    email_recipient: str = Field(
        "recipient@example.com", alias="EMAIL_RECIPIENT"
    )  # Email recipient

    # SMTP Configuration for Gmail
    smtp_host: str = Field("smtp.gmail.com")
    smtp_pass: str = Field(
        "", alias="GMAIL_APP_PASSWORD"
    )  # Maps to GMAIL_APP_PASSWORD env var

    # Timezone
    tz_local: str = "America/Denver"  # Mountain Time

    # SQLAlchemy database URL. Defaults to local Frigate SQLite DB.
    # Example: "sqlite:////home/hunter/frigate/config/frigate.db"
    db_url: str = Field(
        "sqlite:////home/hunter/frigate/config/frigate.db",
    )

    # Frigate base URL for API access and links (without trailing slash)
    frigate_base_url: str = Field("http://localhost:5000", alias="FRIGATE_BASE_URL")

    @computed_field(return_type=ZoneInfo)
    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.tz_local)

    # Computed property for SMTP user (same as sender for Gmail)
    @computed_field(return_type=str)
    @property
    def smtp_user(self) -> str:
        return self.email_sender


settings = Settings()  # import-time singleton
