from pydantic import BaseSettings, Field, computed_field


class Settings(BaseSettings):
    smtp_host: str = Field("smtp.gmail.com", env="SMTP_HOST")
    smtp_user: str
    smtp_pass: str
    tz_local: str = "America/Denver"  # Mountain Time

    @computed_field
    @property
    def tz(self):
        from zoneinfo import ZoneInfo

        return ZoneInfo(self.tz_local)


settings = Settings()  # import-time singleton
