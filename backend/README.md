# HR Portal Backend

FastAPI backend for the HR Management Portal.

## Local development

1. Create and activate a Python 3.10+ virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set a unique local `JWT_SECRET_KEY`.
4. Start from this directory with `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.

The development environment seeds a demo HR Manager account (`alex.morgan@northstar.io` / `password123`). Do not use this account or password in a deployed environment. Demo seeding is disabled when `APP_ENV=production`.

For a production database with no users, run `python create_admin.py` from this directory in a trusted deployment/operations session. It prompts for the first HR Manager and hashes the password; it does not expose a public admin-registration endpoint.

## Replace local demo employees with real staff

1. Stop the backend server.
2. In `backend/.env`, set `SEED_DEMO_DATA=false` (keep `APP_ENV=development` for the local SQLite database). This stops the starter records from being re-created.
3. From the backend directory, run `python remove_demo_employees.py` and confirm by typing `REMOVE DEMO EMPLOYEES`.
4. The script backs up the SQLite database before changes, removes only the four known starter employee records, preserves the Alex Morgan HR Manager login, and retains leave history.
5. Restart the backend, sign in as the HR Manager, go to Employees → Add employee, and enter the real staff member's information. Registration creates the employee account and onboarding checklist.

Do not run the cleanup script against production; it explicitly refuses `APP_ENV=production` and only supports the local SQLite demo database. Review the printed employee list before confirming. Store real staff data only in an appropriately secured deployment.

## New-hire onboarding

Registering a new employee creates an employee record, hashed-password account, profile, and seven onboarding tasks in one database transaction. HR Managers can view progress at `/employees/{id}/onboarding` and update task status through `/employees/onboarding/tasks/{task_id}`.

Employee profile fields are limited to operational contact information and emergency-contact details. Do not store Aadhaar, PAN, bank account details, identity documents, medical data, or other highly sensitive information in this starter application.

## Employee lifecycle

HR Managers can use the Lifecycle page for probation reviews, transfer/promotion proposals, resignation approval, exit-clearance checklist completion, and offboarding. Lifecycle cases are retained as history. Transfers and promotions are applied when their approved effective date arrives and are marked Applied. Resignation does not disable access immediately: HR approval starts exit clearance, and account access is disabled only after every clearance task is completed and HR completes offboarding. Completed offboarding uses the canonical employee status `Inactive`; the resignation case and status history retain the reason and lifecycle record. The current probation period is a configurable-by-code baseline of 180 days; confirm the organization's policy before use. Salary in lifecycle proposals is retained as a text value for history only and is not wired to payroll.

## Paid leave tracking

The Paid Leave HR page reads from a signed audit ledger. Its initial policy is 1 day/month during a 180-day probation and 2.5 days/month after probation; HR Managers can schedule future policy versions from the policy panel. Accrual is prorated by eligible calendar days in the joining/transition month, rounded to 0.01 days, and stops at the recorded employment end date. Approved requests in configured paid leave types debit the balance once at approval; cancellation adds a separate reversal. Pending/rejected/unpaid requests do not debit. Full-day deductions count weekdays and exclude India's three national days; half-days debit 0.5 on eligible weekdays.

The report balance is calculated as **credited (including signed HR adjustments) − net approved paid leave usage**. Every monthly accrual, approval debit, cancellation reversal, and HR adjustment has a unique source key and audit row. A configured policy update takes effect on the first day of next month and is retained as a policy version. HR can add signed balance adjustments with a required reason. Negative balances are blocked by default unless HR enables that policy.

Apply the full Alembic chain (`alembic -c alembic.ini upgrade head`) before using Paid Leave on an existing database. This includes the ledger/policy migration and leave approval timestamp. Historical leave rows without an approval timestamp are backfilled on first ledger reconciliation using their requested leave start date. Review historical employee joining dates and paid leave types before using reports for payroll or statutory decisions. CSV export is Excel-compatible; PDF export uses the browser's print-to-PDF workflow.

## Production deployment is not yet certified

## Employee 360

Authenticated employees can read `/me/360` (or their own `/employees/{id}/360`) for
performance, attendance and leave aggregates, goals, development plans, and document
metadata. HR Managers can view any employee, manage document/certification metadata,
and use `/employees/{id}/360/summary` as an export-friendly aggregate. Goal and
development-plan records support employee self-service create/update. Document
endpoints intentionally store metadata only; raw identity or certificate files are
not accepted or persisted.

The project now has expiring signed access tokens, authenticated API dependencies, role checks on HR administration, configurable database/CORS settings, and a startup guard against SQLite or weak signing keys in production. Before deploying real employee data, an operator must still:

- Set `APP_ENV=production`, a unique random `JWT_SECRET_KEY` (at least 32 characters), `DATABASE_URL` for managed PostgreSQL (for example `postgresql+psycopg://...`), and exact trusted `CORS_ORIGINS` using a secret manager.
- Use HTTPS, deploy behind a trusted reverse proxy, restrict database network access, configure encrypted backups and test restore procedures.
- Apply the included Alembic migration (`alembic -c alembic.ini upgrade head`) before deploying; create future schema changes with Alembic revisions and review the generated SQL.
- Configure centralized logs/alerts, rate limiting, brute-force protection, secret rotation, dependency scanning, and an incident-response process.
- Review India-specific privacy, employment, retention, consent, payroll, and regional holiday policies with qualified counsel and HR/payroll operators.
- Replace demo seed data, set up verified invitation/password-reset delivery, and test access control with dedicated HR and employee accounts.

The `.env.example` file documents configuration variable names only. Keep actual secrets and production credentials out of source control.
