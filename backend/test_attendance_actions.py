import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.config import settings
from app.models.attendance import AttendanceRecord
from app.schemas.attendance import AttendanceRecordCreate


class AttendanceActionTests(unittest.TestCase):
    @staticmethod
    def attendance_payload():
        return AttendanceRecordCreate(
            employee_name="Alex Morgan",
            employee_email="alex.morgan@northstar.io",
            date=date.today().isoformat(),
            latitude=settings.office_latitude,
            longitude=settings.office_longitude,
            accuracy_meters=1,
        )

    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    @patch("app.attendance.routes._verify_employee_face")
    def test_check_in_and_check_out_create_real_attendance_entry(self, _verify_face):
        from app.attendance.routes import check_in_employee, check_out_employee

        checkin = check_in_employee(
            employee_name="Alex Morgan",
            employee_email="alex.morgan@northstar.io",
            payload=self.attendance_payload(),
            db=self.db,
        )

        self.assertIsNotNone(checkin)
        self.assertIn("employee_name", checkin)
        self.assertIsNotNone(checkin["check_in"])

        with self.assertRaises(HTTPException):
            check_in_employee(
                employee_name="Alex Morgan",
                employee_email="alex.morgan@northstar.io",
                payload=self.attendance_payload(),
                db=self.db,
            )

        checkout = check_out_employee(
            employee_name="Alex Morgan",
            employee_email="alex.morgan@northstar.io",
            payload=self.attendance_payload(),
            db=self.db,
        )

        self.assertIsNotNone(checkout)
        self.assertIsNotNone(checkout["check_out"])

    def test_checkout_before_checkin_is_rejected(self):
        from app.attendance.routes import check_out_employee

        with self.assertRaises(HTTPException):
            check_out_employee(
                employee_name="Alex Morgan",
                employee_email="alex.morgan@northstar.io",
                payload=self.attendance_payload(),
                db=self.db,
            )


if __name__ == "__main__":
    unittest.main()
