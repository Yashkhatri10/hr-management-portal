import unittest
from datetime import timedelta

from fastapi import HTTPException
from pydantic import ValidationError

from app.auth.security import create_access_token, decode_access_token
from app.config import Settings


class AuthSecurityTests(unittest.TestCase):
    def test_access_token_round_trip(self):
        token = create_access_token(23, "Employee", "employee@example.com")
        claims = decode_access_token(token)
        self.assertEqual(claims["sub"], 23)
        self.assertEqual(claims["role"], "Employee")
        self.assertEqual(claims["email"], "employee@example.com")

    def test_tampered_token_is_rejected(self):
        token = create_access_token(23, "Employee", "employee@example.com")
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        with self.assertRaises(HTTPException):
            decode_access_token(tampered)

    def test_expired_token_is_rejected(self):
        token = create_access_token(23, "Employee", "employee@example.com", expires_in_seconds=-1)
        with self.assertRaises(HTTPException):
            decode_access_token(token)

    def test_production_settings_require_strong_key_and_managed_database(self):
        with self.assertRaises(ValidationError):
            Settings(app_env="production")

        settings = Settings(
            app_env="production",
            database_url="postgresql+psycopg://user:pass@db/hr",
            jwt_secret_key="x" * 40,
            cors_origins="https://hr.example.com,https://admin.example.com",
        )
        self.assertEqual(settings.cors_origin_list, ["https://hr.example.com", "https://admin.example.com"])

    def test_production_settings_reject_sqlite(self):
        with self.assertRaises(ValidationError):
            Settings(app_env="production", jwt_secret_key="x" * 40)

    def test_production_settings_reject_example_placeholder_secret(self):
        with self.assertRaises(ValidationError):
            Settings(
                app_env="production",
                database_url="postgresql+psycopg://user:pass@db/hr",
                jwt_secret_key="replace-with-a-random-secret-of-at-least-32-characters",
            )

    def test_demo_data_seeding_can_be_disabled(self):
        self.assertTrue(Settings().seed_demo_data)
        self.assertFalse(Settings(seed_demo_data=False).seed_demo_data)


if __name__ == "__main__":
    unittest.main()
