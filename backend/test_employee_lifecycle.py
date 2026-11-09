import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.employees.lifecycle_routes import (
    complete_offboarding,
    create_lifecycle_case,
    decide_lifecycle_case,
    get_employee_lifecycle,
    record_probation_decision,
    update_exit_clearance,
)
from app.models.employee import Employee
from app.models.employee_profile import EmployeeProfile
from app.models.exit_clearance import ExitClearanceItem
from app.models.lifecycle_case import LifecycleCase
from app.models.user import User
from app.schemas.lifecycle import ClearanceUpdate, LifecycleCaseCreate, LifecycleDecision


class EmployeeLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.employee = Employee(
            name="Lifecycle Test", email="lifecycle@example.com", role="Analyst",
            department="People", location="Bengaluru", manager="HR Lead", status="Active", is_active=True,
        )
        self.hr = User(id=1, name="HR Lead", email="hr@example.com", password="hash", role="HR Manager", is_active=True)
        self.db.add_all([self.employee, self.hr])
        self.db.flush()
        self.db.add(EmployeeProfile(employee_id=self.employee.id, start_date=date.today(), employment_type="Full-time"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_transfer_approval_applies_changes_on_effective_date(self):
        result = create_lifecycle_case(
            self.employee.id,
            LifecycleCaseCreate(case_type="Transfer", effective_date=date.today(), reason="Team move", department="Engineering"),
            self.db,
            self.hr,
        )
        case_id = result["cases"][0]["id"]
        decide_lifecycle_case(case_id, LifecycleDecision(status="Approved"), self.db, self.hr)
        updated = get_employee_lifecycle(self.employee.id, self.db)
        self.assertEqual(updated["department"], "Engineering")
        self.assertEqual(updated["cases"][0]["status"], "Applied")

    def test_resignation_requires_clearance_before_offboarding(self):
        result = create_lifecycle_case(
            self.employee.id,
            LifecycleCaseCreate(case_type="Resignation", effective_date=date.today(), last_working_date=date.today(), reason="Moving on"),
            self.db,
            self.hr,
        )
        case_id = result["cases"][0]["id"]
        self.assertEqual(self.db.query(ExitClearanceItem).filter(ExitClearanceItem.case_id == case_id).count(), 6)
        decide_lifecycle_case(case_id, LifecycleDecision(status="Approved"), self.db, self.hr)

        with self.assertRaises(HTTPException) as error:
            complete_offboarding(case_id, self.db, self.hr)
        self.assertEqual(error.exception.status_code, 409)

        items = self.db.query(ExitClearanceItem).filter(ExitClearanceItem.case_id == case_id).all()
        for item in items:
            update_exit_clearance(item.id, ClearanceUpdate(status="Completed"), self.db, self.hr)
        complete_offboarding(case_id, self.db, self.hr)
        self.db.refresh(self.employee)
        self.assertEqual(self.employee.status, "Inactive")
        self.assertFalse(self.employee.is_active)

    def test_probation_extension_is_recorded_and_changes_due_date(self):
        record_probation_decision(self.employee.id, {"decision": "Extended", "extension_days": 30, "notes": "Needs more time"}, self.db, self.hr)
        result = get_employee_lifecycle(self.employee.id, self.db)
        self.assertEqual(result["probation_status"], "Extended")
        self.assertEqual((result["probation_due_date"] - result["start_date"]).days, 210)


if __name__ == "__main__":
    unittest.main()
