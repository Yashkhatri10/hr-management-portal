import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.employee import Employee
from app.models.employee_profile import EmployeeProfile
from app.models.leave_request import LeaveRequest
from app.models.lifecycle_case import LifecycleCase
from app.models.paid_leave_ledger import PaidLeaveLedgerEntry
from app.models.paid_leave_policy import PaidLeavePolicy
from app.models.user import User
from app.services.paid_leave import (
    business_leave_days,
    ensure_ledger_current,
    get_policy,
    ledger_balance,
    record_paid_leave_debit,
    reverse_paid_leave_debit,
    summarize_employee,
    today_local,
)


class PaidLeaveTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.hr = User(name="HR", email="paid-leave-hr@example.com", password="hash", role="HR Manager", is_active=True)
        self.employee = Employee(
            name="Paid Leave User", email="paid-leave-user@example.com", role="Analyst", department="Finance",
            location="Mumbai", status="Active", manager="HR", is_active=True,
        )
        self.db.add_all([self.hr, self.employee])
        self.db.flush()
        self.db.add(EmployeeProfile(employee_id=self.employee.id, start_date=today_local().replace(day=1), employment_type="Full-time"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_probation_accrual_is_prorated_and_idempotent(self):
        policy = get_policy(self.db)
        self.assertEqual(Decimal(policy.probation_monthly_days), Decimal("1.00"))
        ensure_ledger_current(self.db)
        first_balance = ledger_balance(self.db, self.employee.id)
        first_count = self.db.query(PaidLeaveLedgerEntry).filter(PaidLeaveLedgerEntry.employee_id == self.employee.id).count()
        ensure_ledger_current(self.db)
        second_balance = ledger_balance(self.db, self.employee.id)
        second_count = self.db.query(PaidLeaveLedgerEntry).filter(PaidLeaveLedgerEntry.employee_id == self.employee.id).count()

        import calendar
        expected = (Decimal(today_local().day) / Decimal(calendar.monthrange(today_local().year, today_local().month)[1])).quantize(Decimal("0.01"))
        self.assertEqual(first_balance, expected)
        self.assertEqual(second_balance, first_balance)
        self.assertEqual(second_count, first_count)
        summary = summarize_employee(self.db, self.employee, today_local())
        self.assertEqual(summary["employment_status"], "Probation")
        self.assertEqual(summary["monthly_entitlement"], Decimal("1.00"))

    def test_employee_completes_probation_automatically_from_join_date(self):
        profile = self.db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == self.employee.id).one()
        profile.start_date = today_local() - timedelta(days=181)
        self.db.commit()
        ensure_ledger_current(self.db)
        summary = summarize_employee(self.db, self.employee, today_local())
        self.assertEqual(summary["employment_status"], "Regular")
        self.assertEqual(summary["monthly_entitlement"], Decimal("2.50"))

    def test_same_day_probation_confirmation_trueup_is_unique(self):
        profile = self.db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == self.employee.id).one()
        profile.start_date = today_local().replace(day=1)
        ensure_ledger_current(self.db)
        self.db.add(LifecycleCase(
            employee_id=self.employee.id,
            case_type="Probation",
            status="Recorded",
            effective_date=today_local(),
            reason="Confirmed",
            changes_json='{"decision":"Confirmed","extension_days":0}',
            created_by=self.hr.email,
        ))
        self.db.commit()
        ensure_ledger_current(self.db)
        ensure_ledger_current(self.db)
        credits = self.db.query(PaidLeaveLedgerEntry).filter(
            PaidLeaveLedgerEntry.employee_id == self.employee.id,
            PaidLeaveLedgerEntry.entry_type == "CREDIT",
            PaidLeaveLedgerEntry.period_key == today_local().strftime("%Y-%m"),
        ).all()
        self.assertGreater(len(credits), 1)
        self.assertEqual(len({entry.source_key for entry in credits}), len(credits))
        summary = summarize_employee(self.db, self.employee, today_local())
        self.assertEqual(summary["employment_status"], "Regular")

    def test_approved_paid_leave_is_debited_once_and_cancellation_reverses_it(self):
        profile = self.db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == self.employee.id).one()
        profile.start_date = date(today_local().year - 1, 1, 1)
        request = LeaveRequest(
            employee_name=self.employee.name, employee_email=self.employee.email, leave_type="Paid Leave",
            start_date="2026-10-19", end_date="2026-10-20", reason="Personal", status="Approved",
        )
        self.db.add(request)
        self.db.commit()
        ensure_ledger_current(self.db)
        ensure_ledger_current(self.db)
        debits = self.db.query(PaidLeaveLedgerEntry).filter(PaidLeaveLedgerEntry.source_key == f"leave-debit:{request.id}").count()
        self.assertEqual(debits, 1)
        self.assertEqual(business_leave_days(request), Decimal("2.00"))
        before_cancel = ledger_balance(self.db, self.employee.id)

        reverse_paid_leave_debit(self.db, request, self.hr.email)
        request.status = "Cancelled"
        self.db.commit()
        after_cancel = ledger_balance(self.db, self.employee.id)
        self.assertEqual(after_cancel, before_cancel + Decimal("2.00"))
        summary = summarize_employee(self.db, self.employee, today_local())
        self.assertEqual(summary["total_taken"], Decimal("0.00"))

    def test_future_approved_leave_reservation_and_reversal_share_original_period(self):
        from app.services.paid_leave import record_paid_leave_debit

        profile = self.db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == self.employee.id).one()
        profile.start_date = date(today_local().year - 1, 1, 1)
        future_start = today_local() + timedelta(days=45)
        while future_start.weekday() >= 5:
            future_start += timedelta(days=1)
        request = LeaveRequest(
            employee_name=self.employee.name,
            employee_email=self.employee.email,
            leave_type="Annual",
            start_date=future_start.isoformat(),
            end_date=future_start.isoformat(),
            reason="Future appointment",
            status="Approved",
            approved_at=datetime.now(timezone.utc),
        )
        self.db.add(request)
        self.db.commit()
        record_paid_leave_debit(self.db, request, self.hr.email)
        self.db.commit()
        debit = self.db.query(PaidLeaveLedgerEntry).filter(PaidLeaveLedgerEntry.source_key == f"leave-debit:{request.id}").one()
        before = ledger_balance(self.db, self.employee.id)
        reverse_paid_leave_debit(self.db, request, self.hr.email)
        self.db.commit()
        reversal = self.db.query(PaidLeaveLedgerEntry).filter(PaidLeaveLedgerEntry.source_key == f"leave-reversal:{request.id}").one()
        self.assertEqual(reversal.period_key, debit.period_key)
        self.assertEqual(ledger_balance(self.db, self.employee.id), before + Decimal("1.00"))

    def test_pending_and_non_paid_leave_do_not_deduct_balance(self):
        profile = self.db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == self.employee.id).one()
        profile.start_date = date(today_local().year - 1, 1, 1)
        self.db.add_all([
            LeaveRequest(employee_name=self.employee.name, employee_email=self.employee.email, leave_type="Paid Leave", start_date="2026-10-19", end_date="2026-10-20", reason="Pending", status="Pending"),
            LeaveRequest(employee_name=self.employee.name, employee_email=self.employee.email, leave_type="Sick", start_date="2026-10-19", end_date="2026-10-20", reason="Sick", status="Approved"),
        ])
        self.db.commit()
        ensure_ledger_current(self.db)
        self.assertEqual(self.db.query(PaidLeaveLedgerEntry).filter(PaidLeaveLedgerEntry.entry_type == "DEBIT").count(), 0)

    def test_half_day_and_insufficient_balance_are_supported(self):
        half_day = LeaveRequest(
            employee_name=self.employee.name, employee_email=self.employee.email, leave_type="Annual",
            start_date="2026-10-19", end_date="2026-10-19", reason="Appointment", status="Pending", is_half_day=True,
        )
        self.assertEqual(business_leave_days(half_day), Decimal("0.50"))
        ensure_ledger_current(self.db)
        over_request = LeaveRequest(
            employee_name=self.employee.name, employee_email=self.employee.email, leave_type="Paid Leave",
            start_date="2026-10-26", end_date="2026-10-27", reason="Trip", status="Pending",
        )
        self.db.add(over_request)
        self.db.commit()
        record_paid_leave_debit(self.db, over_request, self.hr.email)
        self.assertGreaterEqual(over_request.paid_days, Decimal("0.00"))
        self.assertGreater(over_request.unpaid_days, Decimal("0.00"))
        self.assertEqual(over_request.paid_days + over_request.unpaid_days, Decimal("2.00"))

    def test_policy_change_is_effective_on_its_date_and_keeps_history(self):
        active_policy = get_policy(self.db)
        future = today_local().replace(day=1)
        if today_local().month == 12:
            future = date(today_local().year + 1, 1, 1)
        else:
            future = date(today_local().year, today_local().month + 1, 1)
        scheduled = PaidLeavePolicy(
            effective_from=future,
            probation_days=120,
            probation_monthly_days=Decimal("0.75"),
            regular_monthly_days=Decimal("3.00"),
            paid_leave_types_json='["Annual"]',
            allow_negative_balance=False,
            updated_by=self.hr.email,
        )
        self.db.add(scheduled)
        self.db.commit()
        self.assertEqual(Decimal(get_policy(self.db).regular_monthly_days), Decimal("3.00"))
        self.assertEqual(Decimal(get_policy(self.db, today_local()).regular_monthly_days), Decimal("2.50"))

    def test_report_contains_required_balance_and_utilization_fields(self):
        from app.paid_leave.routes import paid_leave_report

        result = paid_leave_report(
            period_type="month",
            period=today_local().strftime("%Y-%m"),
            search="paid-leave-user",
            department="",
            designation="",
            probation_status="",
            employment_status="",
            sort_by="employee_name",
            db=self.db,
            _hr=self.hr,
        )
        self.assertEqual(len(result["employees"]), 1)
        row = result["employees"][0]
        for field in ("employee_id", "date_of_joining", "monthly_entitlement", "total_credited", "total_taken", "remaining_balance", "pending_requests", "utilization_percent", "exhausted", "overdrawn"):
            self.assertIn(field, row)

    def test_adjustment_is_signed_and_audited(self):
        from app.services.paid_leave import add_adjustment

        ensure_ledger_current(self.db)
        adjustment = add_adjustment(self.db, self.employee.id, Decimal("0.50"), today_local(), "Carryover correction", self.hr.email)
        summary = summarize_employee(self.db, self.employee, today_local())
        self.assertEqual(Decimal(adjustment.amount), Decimal("0.50"))
        self.assertEqual(summary["manual_adjustments"], Decimal("0.50"))
        self.assertGreaterEqual(summary["remaining_balance"], summary["total_credited"])

    def test_paid_leave_balance_formula_includes_adjustments(self):
        from app.services.paid_leave import add_adjustment

        ensure_ledger_current(self.db)
        add_adjustment(self.db, self.employee.id, Decimal("0.50"), today_local(), "Opening correction", self.hr.email)
        summary = summarize_employee(self.db, self.employee, today_local())
        self.assertEqual(summary["remaining_balance"], summary["total_credited"] - summary["total_taken"])


if __name__ == "__main__":
    unittest.main()
