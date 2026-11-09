import math

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HR Management Portal"
    database_url: str = "sqlite:///./hr_portal.db"
    app_env: str = "development"
    app_timezone: str = "Asia/Kolkata"
    seed_demo_data: bool = True
    jwt_secret_key: str = "development-only-change-this-secret"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    office_latitude: float = 28.513393
    office_longitude: float = 77.072276
    office_geofence_radius_meters: float = 900
    max_gps_accuracy_meters: float = 900
    auto_checkout_on_geofence_exit: bool = True
    auto_logout_on_geofence_exit: bool = False
    geofence_monitor_interval_seconds: int = 30
    geofence_exit_confirmations: int = 3
    geofence_exit_grace_period_seconds: int = 120

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if self.app_env.lower() != "production":
            if "http://localhost:5173" in origins and "http://127.0.0.1:5173" not in origins:
                origins.append("http://127.0.0.1:5173")
            if "http://127.0.0.1:5173" in origins and "http://localhost:5173" not in origins:
                origins.append("http://localhost:5173")
        return origins

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if (
            not all(math.isfinite(value) for value in (
                self.office_latitude, self.office_longitude,
                self.office_geofence_radius_meters, self.max_gps_accuracy_meters,
            ))
            or not -90 <= self.office_latitude <= 90
            or not -180 <= self.office_longitude <= 180
            or self.office_geofence_radius_meters <= 0
            or self.max_gps_accuracy_meters <= 0
            or self.geofence_monitor_interval_seconds <= 0
            or self.geofence_exit_confirmations <= 0
            or self.geofence_exit_grace_period_seconds <= 0
        ):
            raise ValueError("Office coordinates and GPS thresholds must be finite and valid")
        if self.app_env.lower() == "production":
            if (
                self.jwt_secret_key == "development-only-change-this-secret"
                or len(self.jwt_secret_key) < 32
                or "replace-with" in self.jwt_secret_key.lower()
                or "placeholder" in self.jwt_secret_key.lower()
            ):
                raise ValueError("Set JWT_SECRET_KEY to a random value of at least 32 characters in production")
            if self.database_url.startswith("sqlite:"):
                raise ValueError("Production requires a managed database; SQLite is for local development only")
        return self


settings = Settings()
