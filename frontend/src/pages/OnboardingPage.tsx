import { useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { getEmployeeOnboarding, getOnboardingDashboard, updateOnboardingTask, type OnboardingDashboardData, type OnboardingDetails, type OnboardingTask } from '../services/api';
import type { Employee } from '../types';

type OnboardingPageProps = { employees: Employee[]; onEmployeeActivated: () => Promise<void> };

export function OnboardingPage({ employees, onEmployeeActivated }: OnboardingPageProps) {
  const [employeeId, setEmployeeId] = useState<number | null>(employees[0]?.id ?? null);
  const [onboarding, setOnboarding] = useState<OnboardingDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dashboard, setDashboard] = useState<OnboardingDashboardData | null>(null);

  useEffect(() => {
    void getOnboardingDashboard().then(setDashboard).catch(() => setDashboard(null));
  }, []);

  useEffect(() => {
    if (employeeId === null) {
      setOnboarding(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError('');
    getEmployeeOnboarding(employeeId)
      .then((data) => { if (active) setOnboarding(data); })
      .catch((loadError: unknown) => { if (active) setError(loadError instanceof Error ? loadError.message : 'Unable to load onboarding.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [employeeId]);

  useEffect(() => {
    if (employeeId === null && employees.length > 0) setEmployeeId(employees[0].id);
    if (employeeId !== null && !employees.some((employee) => employee.id === employeeId)) {
      setEmployeeId(employees[0]?.id ?? null);
    }
  }, [employees, employeeId]);

  const setTaskStatus = async (task: OnboardingTask, status: OnboardingTask['status']) => {
    setError('');
    try {
      const result = await updateOnboardingTask(task.id, status);
      if (employeeId !== null) setOnboarding(await getEmployeeOnboarding(employeeId));
      if (result.employee_status === 'Active') {
        await onEmployeeActivated();
      }
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Unable to update onboarding task.');
    }
  };

  const selectedEmployee = employees.find((employee) => employee.id === employeeId);

  return (
    <Layout title="Onboarding" subtitle="New hire process">
      <section className="surface-card" style={styles.card}>
        <div style={styles.header}>
          <div>
            <h2 style={styles.heading}>Employee onboarding</h2>
            <p style={styles.muted}>Track essential new-hire tasks from offer acceptance through the first day.</p>
          </div>
          <label style={styles.selectLabel}>
            Employee
            <select value={employeeId ?? ''} onChange={(event) => setEmployeeId(Number(event.target.value))} style={styles.select}>
              {employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.name}</option>)}
            </select>
          </label>
        </div>

        {error && <p role="alert" style={styles.error}>{error}</p>}
        {dashboard && <div style={styles.summaryGrid}>{[
          ['Total', dashboard.summary.total],
          ['Pre-boarding', dashboard.summary.preboarding],
          ['In progress', dashboard.summary.in_progress],
          ['Completed', dashboard.summary.completed],
          ['Pending documents', dashboard.summary.pending_documents],
          ['Overdue tasks', dashboard.summary.overdue_tasks],
        ].map(([label, value]) => <div key={label} style={styles.summaryCard}><span style={styles.label}>{label}</span><strong style={styles.summaryValue}>{value}</strong></div>)}</div>}
        {dashboard && <div style={styles.dashboardList}>{dashboard.employees.filter((row) => row.documents_pending > 0 || row.overdue_tasks > 0).slice(0, 8).map((row) => <button key={row.employee_id} type="button" style={styles.dashboardRow} onClick={() => setEmployeeId(row.employee_id)}><span><strong>{row.employee_name}</strong><small style={styles.muted}>{row.department} · {row.status}</small></span><span style={styles.muted}>{row.documents_pending ? `${row.documents_pending} document(s)` : `${row.overdue_tasks} overdue`}</span></button>)}</div>}
        {employees.length === 0 && <p style={styles.muted}>Register an employee first to create an onboarding checklist.</p>}
        {loading && <p style={styles.muted}>Loading onboarding checklist…</p>}

        {!loading && onboarding && selectedEmployee && (
          <>
            <div style={styles.profileGrid}>
              <div><span style={styles.label}>Role</span><strong>{selectedEmployee.role}</strong></div>
              <div><span style={styles.label}>Department</span><strong>{selectedEmployee.department}</strong></div>
              <div><span style={styles.label}>Start date</span><strong>{onboarding.start_date || 'Not provided'}</strong></div>
              <div><span style={styles.label}>Employment</span><strong>{onboarding.employment_type || 'Not provided'}</strong></div>
              <div><span style={styles.label}>Phone</span><strong>{onboarding.phone || 'Not provided'}</strong></div>
              <div><span style={styles.label}>Emergency contact</span><strong>{onboarding.emergency_contact_name ? `${onboarding.emergency_contact_name}${onboarding.emergency_contact_relationship ? ` (${onboarding.emergency_contact_relationship})` : ''} · ${onboarding.emergency_contact_phone || 'phone not provided'}` : 'Not provided'}</strong></div>
            </div>
            <div style={styles.progressHeading}><strong>Checklist progress</strong><strong>{onboarding.progress_percent}%</strong></div>
            <div style={styles.progressTrack}><div style={{ ...styles.progressBar, width: `${onboarding.progress_percent}%` }} /></div>
            <div style={styles.taskList}>
              {onboarding.tasks.map((task) => (
                <article key={task.id} style={styles.task}>
                  <div style={styles.taskContent}>
                    <strong>{task.title}</strong>
                    <span style={styles.muted}>{task.description}</span>
                    <small style={styles.muted}>Owner: {task.owner}{task.due_date ? ` · Due ${task.due_date}` : ''}{task.completed_at ? ` · Completed ${new Date(task.completed_at).toLocaleDateString()}` : ''}</small>
                  </div>
                  <select aria-label={`${task.title} status`} value={task.status} style={styles.statusSelect} onChange={(event) => setTaskStatus(task, event.target.value as OnboardingTask['status'])}>
                    <option>Not started</option><option>In progress</option><option>Completed</option>
                  </select>
                </article>
              ))}
            </div>
          </>
        )}
      </section>
    </Layout>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: { background: '#fff', borderRadius: '20px', padding: '24px', border: '1px solid #e2e8f0' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '20px', flexWrap: 'wrap', marginBottom: '24px' },
  heading: { margin: '0 0 6px', fontSize: '1.35rem' },
  muted: { display: 'block', margin: 0, color: '#64748b', fontSize: '0.86rem', lineHeight: 1.5 },
  selectLabel: { display: 'flex', flexDirection: 'column', gap: '7px', color: '#475569', fontSize: '0.82rem', fontWeight: 700 },
  select: { minWidth: '220px', padding: '10px 12px', border: '1px solid #cbd5e1', borderRadius: '10px', background: '#fff' },
  profileGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '16px', padding: '18px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '14px' },
  summaryGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px', marginBottom: '18px' },
  summaryCard: { padding: '14px', border: '1px solid #e2e8f0', borderRadius: '12px', background: '#f8fafc' },
  summaryValue: { display: 'block', fontSize: '1.35rem', color: '#172b46' },
  dashboardList: { display: 'grid', gap: '8px', marginBottom: '20px' },
  dashboardRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', textAlign: 'left', padding: '11px 13px', border: '1px solid #e2e8f0', borderRadius: '10px', background: '#fff', cursor: 'pointer' },
  label: { display: 'block', color: '#64748b', fontSize: '0.74rem', marginBottom: '5px' },
  progressHeading: { display: 'flex', justifyContent: 'space-between', marginTop: '24px', color: '#1e293b' },
  progressTrack: { height: '9px', background: '#e2e8f0', borderRadius: '999px', overflow: 'hidden', margin: '10px 0 20px' },
  progressBar: { height: '100%', background: 'linear-gradient(90deg, #4f46e5, #8b5cf6)', transition: 'width 200ms ease' },
  taskList: { display: 'flex', flexDirection: 'column', gap: '10px' },
  task: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '18px', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '14px 16px' },
  taskContent: { display: 'flex', flexDirection: 'column', gap: '5px' },
  statusSelect: { flexShrink: 0, padding: '9px 10px', border: '1px solid #cbd5e1', borderRadius: '9px', background: '#fff' },
  error: { padding: '12px', borderRadius: '10px', background: '#fee2e2', color: '#991b1b' },
};
