import { useEffect, useState, type FormEvent } from 'react';
import { Layout } from '../components/Layout';
import {
  completeOffboarding,
  createLifecycleCase,
  decideLifecycleCase,
  downloadReport,
  getEmployeeLifecycle,
  recordProbationDecision,
  updateEmployeeLifecycleStatus,
  updateExitClearance,
  type EmployeeLifecycle,
  type EmployeeLifecycleStatus,
  type LifecycleCasePayload,
} from '../services/api';
import type { Employee } from '../types';

type Props = { employees: Employee[]; onRefresh: () => Promise<void> };
type CaseType = LifecycleCasePayload['case_type'];

const initialForm = (): LifecycleCasePayload => ({
  case_type: 'Transfer',
  effective_date: new Date().toISOString().slice(0, 10),
  reason: '',
});

export function EmployeeLifecyclePage({ employees, onRefresh }: Props) {
  const [employeeId, setEmployeeId] = useState<number | null>(employees[0]?.id ?? null);
  const [lifecycle, setLifecycle] = useState<EmployeeLifecycle | null>(null);
  const [form, setForm] = useState<LifecycleCasePayload>(initialForm);
  const [extensionDays, setExtensionDays] = useState(30);
  const [notes, setNotes] = useState('');
  const [status, setStatus] = useState<EmployeeLifecycleStatus>('Active');
  const [statusDate, setStatusDate] = useState(new Date().toISOString().slice(0, 10));
  const [statusReason, setStatusReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const load = async (id: number) => {
    setLoading(true);
    setError('');
    try {
      const nextLifecycle = await getEmployeeLifecycle(id);
      setLifecycle(nextLifecycle);
      setStatus((employees.find((employee) => employee.id === id)?.status || 'Active') as EmployeeLifecycleStatus);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load employee lifecycle.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId !== null) void load(employeeId);
    else setLifecycle(null);
  }, [employeeId]);

  useEffect(() => {
    if (employeeId === null && employees.length) setEmployeeId(employees[0].id);
    else if (employeeId !== null && !employees.some((employee) => employee.id === employeeId)) setEmployeeId(employees[0]?.id ?? null);
  }, [employees, employeeId]);

  const refreshSelected = async () => {
    if (employeeId !== null) await load(employeeId);
    await onRefresh();
  };

  const submitCase = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (employeeId === null) return;
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await createLifecycleCase(employeeId, form);
      setSuccess(`${form.case_type} case submitted for HR review.`);
      setForm(initialForm());
      await refreshSelected();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to submit lifecycle case.');
    } finally {
      setSaving(false);
    }
  };

  const runAction = async (action: () => Promise<unknown>, message: string) => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await action();
      setSuccess(message);
      await refreshSelected();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Action failed.');
    } finally {
      setSaving(false);
    }
  };

  const changeCaseType = (caseType: CaseType) => setForm({ ...initialForm(), case_type: caseType });

  const changeStatus = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (employeeId === null) return;
    await runAction(
      () => updateEmployeeLifecycleStatus(employeeId, { status, effective_date: statusDate, reason: statusReason }),
      `Employee status changed to ${status}.`,
    );
    setStatusReason('');
  };

  const exportLifecycle = async (format: 'csv' | 'xlsx' | 'pdf') => {
    if (employeeId === null) return;
    setSaving(true);
    setError('');
    try {
      await downloadReport('lifecycle', format, { employee_id: employeeId });
      setSuccess(`Lifecycle ${format.toUpperCase()} report downloaded.`);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : 'Unable to download the lifecycle report.');
    } finally {
      setSaving(false);
    }
  };

  const activeCases = lifecycle?.cases ?? [];
  const probationCase = activeCases.find((item) => item.case_type === 'Probation');
  const pendingCase = activeCases.find((item) => item.status === 'Pending');

  return (
    <Layout title="Employee lifecycle" subtitle="People operations">
      <div className="surface-card" style={styles.shell}>
        <div style={styles.topRow}>
          <div>
            <h2 style={styles.heading}>Lifecycle workspace</h2>
            <p style={styles.muted}>Manage probation, role changes, resignation and exit clearance in one place.</p>
          </div>
          <label style={styles.employeePicker}>Employee
            <select value={employeeId ?? ''} onChange={(event) => setEmployeeId(Number(event.target.value))} style={styles.select}>
              {employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.name} · {employee.status}</option>)}
            </select>
          </label>
        </div>

        {error && <div role="alert" className="error-banner" style={styles.message}>{error}</div>}
        {success && <div role="status" style={styles.success}>{success}</div>}
        {!employees.length && <p style={styles.muted}>Register employees to manage their lifecycle.</p>}
        {loading && <p style={styles.muted}>Loading employee lifecycle…</p>}

        {!loading && lifecycle && (
          <>
            <section style={styles.summaryGrid}>
              <div style={styles.summaryCard}><span style={styles.label}>Current role</span><strong>{lifecycle.role}</strong></div>
              <div style={styles.summaryCard}><span style={styles.label}>Department / location</span><strong>{lifecycle.department} · {lifecycle.location}</strong></div>
              <div style={styles.summaryCard}><span style={styles.label}>Manager</span><strong>{lifecycle.manager}</strong></div>
              <div style={styles.summaryCard}><span style={styles.label}>Probation review</span><strong>{lifecycle.probation_status}</strong><small>{lifecycle.probation_due_date || 'Start date unavailable'}</small></div>
            </section>

            <section className="surface-card" style={styles.actionCard}>
              <div>
                <h3 style={styles.subheading}>Status and reports</h3>
                <p style={styles.muted}>Every status change is recorded in lifecycle history. Deactivation never removes employee records.</p>
              </div>
              <form style={styles.statusForm} onSubmit={changeStatus}>
                <select aria-label="Employee status" value={status} style={styles.input} onChange={(event) => setStatus(event.target.value as EmployeeLifecycleStatus)}>
                  <option value="Active">Active</option><option value="On Notice">On notice</option><option value="On Leave">On leave</option>
                  <option value="Resigned">Resigned</option><option value="Terminated">Terminated</option><option value="Inactive">Inactive</option>
                </select>
                <input aria-label="Status effective date" required type="date" value={statusDate} style={styles.input} onChange={(event) => setStatusDate(event.target.value)} />
                <input aria-label="Status change reason" required minLength={3} value={statusReason} placeholder="Reason" style={styles.input} onChange={(event) => setStatusReason(event.target.value)} />
                <button type="submit" className="secondary-action" disabled={saving || statusReason.trim().length < 3}>Save status</button>
              </form>
              <div style={styles.buttonRow}>
                <button type="button" className="secondary-action" disabled={saving} onClick={() => void exportLifecycle('csv')}>Export CSV</button>
                <button type="button" className="secondary-action" disabled={saving} onClick={() => void exportLifecycle('xlsx')}>Export Excel</button>
                <button type="button" className="secondary-action" disabled={saving} onClick={() => void exportLifecycle('pdf')}>Export PDF</button>
              </div>
            </section>

            <section style={styles.probationCard}>
              <div>
                <h3 style={styles.subheading}>Probation tracking</h3>
                <p style={styles.muted}>Standard review due 180 days after start date{lifecycle.probation_due_date ? ` (${lifecycle.probation_due_date})` : ''}.</p>
                {probationCase && <small style={styles.muted}>Latest decision: {probationCase.changes.decision} · {probationCase.reason}</small>}
              </div>
              {lifecycle.probation_status !== 'Confirmed' && (
                <div style={styles.buttonRow}>
                  <button type="button" className="primary-action" disabled={saving || !lifecycle.start_date} onClick={() => void runAction(() => recordProbationDecision(lifecycle.employee_id, 'Confirmed', 0, notes), 'Probation confirmed.')}>Confirm</button>
                  <input aria-label="Probation extension days" type="number" min={1} max={180} value={extensionDays} onChange={(event) => setExtensionDays(Number(event.target.value))} style={styles.daysInput} />
                  <span style={styles.muted}>days</span>
                  <button type="button" className="secondary-action" disabled={saving || !lifecycle.start_date} onClick={() => void runAction(() => recordProbationDecision(lifecycle.employee_id, 'Extended', extensionDays, notes), `Probation extended by ${extensionDays} days.`)}>Extend</button>
                </div>
              )}
            </section>

            <div style={styles.columns}>
              <form className="surface-card" style={styles.formCard} onSubmit={submitCase}>
                <h3 style={styles.subheading}>Start a lifecycle case</h3>
                <label style={styles.field}>Workflow
                  <select value={form.case_type} style={styles.input} onChange={(event) => changeCaseType(event.target.value as CaseType)}>
                    <option value="Transfer">Transfer</option><option value="Promotion">Promotion</option><option value="Resignation">Resignation</option>
                  </select>
                </label>
                <label style={styles.field}>Effective date<input required type="date" value={form.effective_date} style={styles.input} onChange={(event) => setForm({ ...form, effective_date: event.target.value })} /></label>
                {form.case_type === 'Transfer' && <>
                  <label style={styles.field}>New department<input value={form.department || ''} style={styles.input} onChange={(event) => setForm({ ...form, department: event.target.value })} /></label>
                  <label style={styles.field}>New location<input value={form.location || ''} style={styles.input} onChange={(event) => setForm({ ...form, location: event.target.value })} /></label>
                  <label style={styles.field}>New manager<input value={form.manager || ''} style={styles.input} onChange={(event) => setForm({ ...form, manager: event.target.value })} /></label>
                </>}
                {form.case_type === 'Promotion' && <>
                  <label style={styles.field}>New title<input value={form.role || ''} style={styles.input} onChange={(event) => setForm({ ...form, role: event.target.value })} /></label>
                  <label style={styles.field}>New department (optional)<input value={form.department || ''} style={styles.input} onChange={(event) => setForm({ ...form, department: event.target.value })} /></label>
                  <label style={styles.field}>New salary (optional)<input value={form.new_salary || ''} style={styles.input} onChange={(event) => setForm({ ...form, new_salary: event.target.value })} /></label>
                </>}
                {form.case_type === 'Resignation' && <label style={styles.field}>Last working date<input type="date" value={form.last_working_date || ''} style={styles.input} onChange={(event) => setForm({ ...form, last_working_date: event.target.value })} /></label>}
                <label style={styles.field}>Reason<textarea required minLength={3} maxLength={2000} value={form.reason} style={{ ...styles.input, minHeight: '82px', resize: 'vertical' }} onChange={(event) => setForm({ ...form, reason: event.target.value })} /></label>
                <label style={styles.field}>Probation notes (optional)<input value={notes} style={styles.input} onChange={(event) => setNotes(event.target.value)} /></label>
                <button type="submit" className="primary-action" disabled={saving || Boolean(pendingCase)}>{saving ? 'Submitting…' : 'Submit for review'}</button>
                {pendingCase && <small style={styles.muted}>Resolve the pending {pendingCase.case_type.toLowerCase()} case before starting another.</small>}
              </form>

              <section className="surface-card" style={styles.historyCard}>
                <h3 style={styles.subheading}>Lifecycle history</h3>
                {!activeCases.length && <p style={styles.muted}>No lifecycle events recorded yet.</p>}
                <div style={styles.caseList}>
                  {activeCases.map((item) => (
                    <article key={item.id} style={styles.caseCard}>
                      <div style={styles.caseHeader}><strong>{item.case_type}</strong><span style={badgeStyle(item.status)}>{item.status}</span></div>
                      <p style={styles.caseReason}>{item.reason}</p>
                      <small style={styles.muted}>Effective {item.effective_date} · Opened by {item.created_by}</small>
                      {Object.entries(item.changes).filter(([, value]) => value).map(([key, value]) => <small key={key} style={styles.changeLine}>{labelFor(key)}: {value}</small>)}
                      {item.status === 'Pending' && <div style={styles.buttonRow}>
                        <button type="button" className="primary-action" disabled={saving} onClick={() => void runAction(() => decideLifecycleCase(item.id, 'Approved'), 'Lifecycle case approved.')}>Approve</button>
                        <button type="button" className="secondary-action" disabled={saving} onClick={() => void runAction(() => decideLifecycleCase(item.id, 'Rejected'), 'Lifecycle case rejected.')}>Reject</button>
                      </div>}
                      {item.case_type === 'Resignation' && item.status === 'Approved' && <div style={styles.clearanceList}>
                        <h4 style={styles.clearanceTitle}>Exit clearance</h4>
                        {item.clearance.map((clearance) => <div key={clearance.id} style={styles.clearanceRow}>
                          <div><strong>{clearance.title}</strong><small style={styles.muted}>Owner: {clearance.owner} · {clearance.status}</small></div>
                          <button type="button" disabled={saving || clearance.status === 'Completed'} className="secondary-action" onClick={() => void runAction(() => updateExitClearance(clearance.id, 'Completed'), `${clearance.title} completed.`)}>{clearance.status === 'Completed' ? 'Done' : 'Complete'}</button>
                        </div>)}
                        <button type="button" disabled={saving || item.clearance.some((clearance) => clearance.status !== 'Completed')} className="primary-action" onClick={() => void runAction(() => completeOffboarding(item.id), 'Offboarding complete. Employee access disabled; history retained.')}>Complete offboarding</button>
                      </div>}
                    </article>
                  ))}
                </div>
              </section>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}

function labelFor(field: string): string {
  return field.replace(/_/g, ' ').replace(/\b\w/g, (letter: string) => letter.toUpperCase());
}

function badgeStyle(status: string): React.CSSProperties {
  const colors: Record<string, [string, string]> = {
    Pending: ['#fff7df', '#8a5600'], Approved: ['#e5f8ef', '#17623e'], Applied: ['#e7efff', '#234e9b'], Rejected: ['#ffeded', '#a33434'], Recorded: ['#e9e8ff', '#4942aa'], Closed: ['#e8edf3', '#435168'],
  };
  const [background, color] = colors[status] || colors.Pending;
  return { padding: '5px 9px', borderRadius: '999px', background, color, fontSize: '.72rem', fontWeight: 800 };
}

const styles: Record<string, React.CSSProperties> = {
  shell: { padding: '24px', borderRadius: '20px' },
  topRow: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '18px', flexWrap: 'wrap', marginBottom: '22px' },
  heading: { margin: '0 0 7px', fontSize: '1.4rem', color: '#13233b' },
  muted: { display: 'block', margin: 0, color: '#61718a', fontSize: '.82rem', lineHeight: 1.45 },
  employeePicker: { display: 'flex', flexDirection: 'column', gap: '6px', color: '#354963', fontWeight: 700, fontSize: '.8rem' },
  select: { minWidth: '260px', padding: '11px 12px', border: '1px solid #cbd7e6', borderRadius: '10px', background: '#fff' },
  message: { padding: '12px', borderRadius: '10px', marginBottom: '14px' },
  success: { padding: '12px', borderRadius: '10px', marginBottom: '14px', background: '#e5f8ef', color: '#17623e' },
  summaryGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '18px' },
  summaryCard: { display: 'flex', flexDirection: 'column', gap: '6px', minWidth: 0, padding: '14px', border: '1px solid #e1e9f2', borderRadius: '12px', background: '#f8faff', color: '#1b304e' },
  label: { color: '#61718a', fontSize: '.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.04em' },
  probationCard: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '18px', flexWrap: 'wrap', padding: '17px', marginBottom: '18px', border: '1px solid #d8e8f0', borderRadius: '14px', background: 'linear-gradient(110deg, #effaf9, #f2f4ff)' },
  actionCard: { display: 'flex', flexDirection: 'column', gap: '12px', padding: '17px', marginBottom: '18px', borderRadius: '14px' },
  statusForm: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px', alignItems: 'center' },
  subheading: { margin: '0 0 12px', color: '#172b46', fontSize: '1.05rem' },
  buttonRow: { display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '12px' },
  daysInput: { width: '78px', padding: '9px', border: '1px solid #cbd7e6', borderRadius: '9px' },
  columns: { display: 'grid', gridTemplateColumns: 'minmax(280px, .82fr) minmax(0, 1.18fr)', alignItems: 'start', gap: '16px' },
  formCard: { display: 'flex', flexDirection: 'column', gap: '12px', padding: '20px', borderRadius: '16px' },
  field: { display: 'flex', flexDirection: 'column', gap: '6px', color: '#354963', fontWeight: 700, fontSize: '.8rem' },
  input: { width: '100%', padding: '10px 12px', border: '1px solid #cbd7e6', borderRadius: '9px', background: '#fff', color: '#152641' },
  historyCard: { padding: '20px', borderRadius: '16px' },
  caseList: { display: 'flex', flexDirection: 'column', gap: '12px' },
  caseCard: { padding: '15px', border: '1px solid #e1e8f0', borderRadius: '13px', background: '#fff' },
  caseHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' },
  caseReason: { margin: '10px 0 6px', color: '#354963', fontSize: '.88rem' },
  changeLine: { display: 'block', marginTop: '5px', color: '#354963', fontSize: '.78rem' },
  clearanceList: { display: 'flex', flexDirection: 'column', gap: '9px', marginTop: '14px', paddingTop: '13px', borderTop: '1px solid #e1e8f0' },
  clearanceTitle: { margin: 0, color: '#1b304e', fontSize: '.9rem' },
  clearanceRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', padding: '10px', borderRadius: '9px', background: '#f7f9fc', color: '#243957', fontSize: '.8rem' },
};
