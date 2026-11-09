import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.attendance import AttendanceRecord


class AttendanceActionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_check_in_and_check_out_create_real_attendance_entry(self):
        from app.attendance.routes import check_in_employee, check_out_employee

        checkin = check_in_employee(
            employee_name="Alex Morgan",
            employee_email="alex.morgan@northstar.io",
            db=self.db,
        )

        self.assertIsNotNone(checkin)
        self.assertIn("employee_name", checkin)
        self.assertIsNotNone(checkin["check_in"])

        with self.assertRaises(HTTPException):
            check_in_employee(
                employee_name="Alex Morgan",
                employee_email="alex.morgan@northstar.io",
                db=self.db,
            )

        checkout = check_out_employee(
            employee_name="Alex Morgan",
            employee_email="alex.morgan@northstar.io",
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
                db=self.db,
            )


if __name__ == "__main__":
    unittest.main()
