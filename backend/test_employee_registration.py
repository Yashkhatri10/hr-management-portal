import unittest
from datetime import date
from uuid import uuid4

from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.employees.routes import register_employee
from app.models.employee import Employee
from app.models.employee_profile import EmployeeProfile
from app.models.onboarding_task import OnboardingTask
from app.models.user import User
from app.schemas.employee import EmployeeRegistration, EmployeeUpdate
from app.schemas.onboarding import OnboardingTaskUpdate


class EmployeeRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.email = f"registration-{uuid4().hex}@example.com"
        self.payload = EmployeeRegistration(
            name="Test Employee",
            email=self.email,
            role="Analyst",
            department="People",
            location="Remote",
            status="Active",
            manager="Alex Morgan",
            password="temporary-pass-123",
            start_date=date.today(),
            employment_type="Full-time",
        )

    def tearDown(self):
        employee = self.db.query(Employee).filter(Employee.email == self.email).first()
        if employee:
            self.db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee.id).delete()
            self.db.query(OnboardingTask).filter(OnboardingTask.employee_id == employee.id).delete()
        self.db.query(Employee).filter(Employee.email == self.email).delete()
        self.db.query(User).filter(User.email == self.email).delete()
        self.db.commit()
        self.db.close()
        self.engine.dispose()

    def test_registration_persists_employee_and_hashed_login(self):
        employee = register_employee(self.payload, self.db)

        self.assertEqual(employee["email"], self.email)
        account = self.db.query(User).filter(User.email == self.email).one()
        self.assertNotEqual(account.password, self.payload.password)
        self.assertTrue(account.password.startswith("$argon2"))
        profile = self.db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee["id"]).one()
        self.assertEqual(profile.start_date, date.today())
        self.assertEqual(self.db.query(OnboardingTask).filter(OnboardingTask.employee_id == employee["id"]).count(), 7)

    def test_onboarding_checklist_completion_activates_employee(self):
        from app.employees.routes import get_employee_onboarding, update_onboarding_task

        employee = register_employee(self.payload, self.db)
        onboarding = get_employee_onboarding(employee["id"], self.db, _hr=None)
        first_task = onboarding["tasks"][0]
        result = update_onboarding_task(first_task.id, OnboardingTaskUpdate(status="Completed"), self.db, _hr=None)

        self.assertEqual(result["status"], "Completed")
        self.assertEqual(result["employee_status"], "Pending")

        for task in onboarding["tasks"]:
            update_onboarding_task(task.id, OnboardingTaskUpdate(status="Completed"), self.db, _hr=None)
        updated_employee = self.db.query(Employee).filter(Employee.id == employee["id"]).one()
        self.assertEqual(updated_employee.status, "Active")

    def test_duplicate_email_is_rejected(self):
        register_employee(self.payload, self.db)

        with self.assertRaises(HTTPException) as error:
            register_employee(self.payload, self.db)

        self.assertEqual(error.exception.status_code, 409)

    def test_employee_details_and_linked_account_can_be_updated(self):
        from app.employees.routes import update_employee

        employee = register_employee(self.payload, self.db)
        new_email = f"updated-{uuid4().hex}@example.com"
        result = update_employee(
            employee["id"],
            EmployeeUpdate(name="Updated Employee", email=new_email, department="Engineering", phone="+91 9000000000"),
            self.db,
            _hr=None,
        )

        self.assertEqual(result["name"], "Updated Employee")
        self.assertEqual(result["email"], new_email)
        self.assertEqual(result["phone"], "+91 9000000000")
        account = self.db.query(User).filter(User.email == new_email).one()
        self.assertEqual(account.name, "Updated Employee")

    def test_archive_disables_account_but_preserves_employee_and_history(self):
        from app.employees.routes import archive_employee

        employee = register_employee(self.payload, self.db)
        result = archive_employee(employee["id"], self.db, current_user=User(id=999, name="HR", email="hr@example.com", password="hash", role="HR Manager", is_active=True), _hr=None)

        stored_employee = self.db.query(Employee).filter(Employee.id == employee["id"]).one()
        account = self.db.query(User).filter(User.email == self.email).one()
        self.assertEqual(result["id"], employee["id"])
        self.assertEqual(stored_employee.status, "Inactive")
        self.assertFalse(stored_employee.is_active)
        self.assertFalse(account.is_active)
        self.assertEqual(self.db.query(OnboardingTask).filter(OnboardingTask.employee_id == employee["id"]).count(), 7)

    def test_current_hr_manager_cannot_archive_self(self):
        from app.employees.routes import archive_employee

        employee = register_employee(self.payload, self.db)
        with self.assertRaises(HTTPException) as error:
            archive_employee(employee["id"], self.db, current_user=User(id=999, name=self.payload.name, email=self.email, password="hash", role="HR Manager", is_active=True), _hr=None)
        self.assertEqual(error.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()