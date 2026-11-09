import { useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { addEmployeeActivity, addEmployeeTask, createMyProgressReport, getMyEmployee360, getMyProgressReports, submitMyProgressReport, updateEmployeeKraProgress, updateEmployeeTask, updateMyKpiActual, type Employee360Data, type ProgressReport } from '../services/api';

export function EmployeeSelfServicePage() {
  const [data, setData] = useState<Employee360Data | null>(null);
  const [error, setError] = useState('');
  const [savingId, setSavingId] = useState<string | null>(null);
  const [newTask, setNewTask] = useState('');
  const [newActivity, setNewActivity] = useState('');
  const [reports, setReports] = useState<ProgressReport[]>([]);
  const [reportSummary, setReportSummary] = useState('');

  const load = async () => {
    try {
      setError('');
      const [dashboard, reportResponse] = await Promise.all([getMyEmployee360(), getMyProgressReports()]);
      setData(dashboard);
      setReports(reportResponse.reports);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load your employee dashboard.');
    }
  };

  useEffect(() => { void load(); }, []);

  const updateTask = async (taskId: number, status: string, progress: number, notes: string) => {
    setSavingId(`task-${taskId}`);
    try {
      await updateEmployeeTask(taskId, { status, progress_percentage: progress, progress_notes: notes });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to update task progress.');
    } finally {
      setSavingId(null);
    }
  };

  const updateKra = async (kraId: number, progress: number, notes: string) => {
    setSavingId(`kra-${kraId}`);
    try {
      await updateEmployeeKraProgress(kraId, { progress_percentage: progress, progress_notes: notes });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to update KRA progress.');
    } finally {
      setSavingId(null);
    }
  };

  const addTask = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newTask.trim() || !data) return;
    setSavingId('new-task');
    try {
      await addEmployeeTask(data.employee.id, { title: newTask.trim(), priority: 'Medium' });
      setNewTask('');
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to add your task.');
    } finally {
      setSavingId(null);
    }
  };

  const addActivity = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newActivity.trim() || !data) return;
    setSavingId('new-activity');
    try {
      await addEmployeeActivity(data.employee.id, { title: newActivity.trim(), activity_type: 'work update' });
      setNewActivity('');
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to add your activity.');
    } finally {
      setSavingId(null);
    }
  };

  const createReport = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!reportSummary.trim()) return;
    setSavingId('new-report');
    const today = new Date().toISOString().slice(0, 10);
    try {
      await createMyProgressReport({ period_type: 'Monthly', period_start: `${today.slice(0, 7)}-01`, period_end: today, summary: reportSummary.trim() });
      setReportSummary('');
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to create progress report.');
    } finally {
      setSavingId(null);
    }
  };

  if (!data) return error ? <Layout title="My Employee Dashboard" subtitle="Self-service"><p role="alert" style={styles.error}>{error}</p><button type="button" onClick={() => void load()}>Retry</button></Layout> : <div className="loading-screen">Loading your employee dashboard...</div>;
  return (
    <Layout title="My Employee Dashboard" subtitle="Self-service">
      {error && <p role="alert" style={styles.error}>{error}</p>}
      <section className="surface-card" style={styles.header}>
        <div><h2 style={{ margin: 0 }}>{data.employee.name}</h2><p style={styles.muted}>{data.employee.role} · {data.employee.department}</p><p style={styles.muted}>Manager: {data.employee.manager || 'Not assigned'} · Status: {data.employee.status}</p></div>
        <div style={styles.metrics}><Metric label="Open tasks" value={data.summary.open_tasks} /><Metric label="Completed" value={data.summary.completed_tasks} /><Metric label="Overdue" value={data.summary.overdue_tasks ?? 0} /><Metric label="KPI score" value={data.summary.average_kpi_score ?? '—'} /></div>
      </section>
      <div style={styles.grid}>
        <section className="surface-card" style={styles.card}>
          <h3 style={styles.title}>My tasks</h3>
          <form onSubmit={(event) => void addTask(event)} style={styles.addForm}><input required value={newTask} onChange={(event) => setNewTask(event.target.value)} placeholder="Add a personal work task" style={styles.input} /><button type="submit" className="primary-action" disabled={savingId === 'new-task'}>{savingId === 'new-task' ? 'Saving…' : 'Add task'}</button></form>
          {data.tasks.length === 0 ? <p style={styles.muted}>No tasks are assigned yet.</p> : data.tasks.map((task) => <TaskEditor key={task.id} task={task} saving={savingId === `task-${task.id}`} onSave={updateTask} />)}
        </section>
        <section className="surface-card" style={styles.card}>
          <h3 style={styles.title}>My KRAs and KPIs</h3>
          {data.kras.length === 0 ? <p style={styles.muted}>No KRAs are assigned yet.</p> : data.kras.map((kra) => <KraEditor key={kra.id} kra={kra} saving={savingId === `kra-${kra.id}`} onSave={updateKra} onKpiSave={async (id, actual, notes) => { await updateMyKpiActual(id, { actual_value: actual, notes }); await load(); }} />)}
        </section>
      </div>
      <section className="surface-card" style={styles.card}>
        <h3 style={styles.title}>My recent activities</h3>
        <form onSubmit={(event) => void addActivity(event)} style={styles.addForm}><input required value={newActivity} onChange={(event) => setNewActivity(event.target.value)} placeholder="Record a work activity" style={styles.input} /><button type="submit" className="primary-action" disabled={savingId === 'new-activity'}>{savingId === 'new-activity' ? 'Saving…' : 'Add activity'}</button></form>
        {data.activities.length === 0 ? <p style={styles.muted}>No activity updates yet.</p> : data.activities.slice(0, 10).map((item) => <div key={item.id} style={styles.item}><strong>{item.title}</strong><span style={styles.muted}> · {item.activity_date}</span><p>{item.description || item.activity_type}</p></div>)}
      </section>
      <div style={styles.grid}>
        <section className="surface-card" style={styles.card}><h3 style={styles.title}>My attendance and leave</h3><p>Attendance rate: {data.attendance?.attendance_rate ?? 0}%</p><p>Present days: {data.attendance?.present ?? 0}</p><p>Approved leave days: {data.leave?.approved_days ?? 0}</p></section>
        <section className="surface-card" style={styles.card}><h3 style={styles.title}>My goals</h3>{(data.goals || []).length === 0 ? <p style={styles.muted}>No goals assigned.</p> : data.goals?.map((goal) => <p key={goal.id}><strong>{goal.title}</strong> · {goal.status} · {goal.progress_percentage}%</p>)}</section>
      </div>
      <section className="surface-card" style={styles.card}>
        <h3 style={styles.title}>My progress reports</h3>
        <form onSubmit={(event) => void createReport(event)} style={styles.addForm}><input required value={reportSummary} onChange={(event) => setReportSummary(event.target.value)} placeholder="Monthly accomplishments and blockers" style={styles.input} /><button type="submit" className="primary-action" disabled={savingId === 'new-report'}>{savingId === 'new-report' ? 'Saving…' : 'Save draft'}</button></form>
        {reports.length === 0 ? <p style={styles.muted}>No progress reports submitted yet.</p> : reports.map((report) => <div key={report.id} style={styles.item}><strong>{report.period_type} · {report.period_start} to {report.period_end}</strong><span style={styles.muted}> · {report.status}</span><p>{report.summary}</p>{report.review_feedback && <p style={styles.muted}>HR feedback: {report.review_feedback}</p>}{report.status === 'Draft' && <button type="button" className="secondary-action" onClick={() => void submitMyProgressReport(report.id).then(load)}>Submit report</button>}</div>)}
      </section>
    </Layout>
  );
}

type Task = Employee360Data['tasks'][number];
function TaskEditor({ task, saving, onSave }: { task: Task; saving: boolean; onSave: (id: number, status: string, progress: number, notes: string) => Promise<void> }) {
  const [status, setStatus] = useState(task.status);
  const [progress, setProgress] = useState(task.progress_percentage ?? (task.status === 'Completed' ? 100 : 0));
  const [notes, setNotes] = useState(task.progress_notes || '');
  return <div style={styles.item}><strong>{task.title}</strong><p style={styles.muted}>{task.description || 'No description'}{task.due_date ? ` · Due ${task.due_date}` : ''}</p><div style={styles.controls}><select value={status} onChange={(event) => setStatus(event.target.value)}><option>Not Started</option><option>In Progress</option><option>Pending</option><option>Completed</option></select><input type="number" min="0" max="100" value={progress} onChange={(event) => setProgress(Number(event.target.value))} aria-label={`Progress for ${task.title}`} /><span>%</span><input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Progress note" /><button type="button" className="primary-action" disabled={saving} onClick={() => void onSave(task.id, status, progress, notes)}>{saving ? 'Saving…' : 'Update'}</button></div></div>;
}

type Kra = Employee360Data['kras'][number];
function KraEditor({ kra, saving, onSave, onKpiSave }: { kra: Kra; saving: boolean; onSave: (id: number, progress: number, notes: string) => Promise<void>; onKpiSave: (id: number, actual: number, notes: string) => Promise<void> }) {
  const [progress, setProgress] = useState(kra.progress_percentage ?? 0);
  const [notes, setNotes] = useState(kra.progress_notes || '');
  return <div style={styles.item}><strong>{kra.title}</strong><p style={styles.muted}>{kra.description || 'No description'} · {kra.period_start} to {kra.period_end}</p><div style={styles.progressBar}><span style={{ width: `${progress}%` }} /></div><div style={styles.controls}><input type="number" min="0" max="100" value={progress} onChange={(event) => setProgress(Number(event.target.value))} aria-label={`Progress for ${kra.title}`} /><span>%</span><input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Achievement or progress note" /><button type="button" className="primary-action" disabled={saving} onClick={() => void onSave(kra.id, progress, notes)}>{saving ? 'Saving…' : 'Update'}</button></div>{kra.kpis.map((kpi) => <KpiEditor key={kpi.id} kpi={kpi} onSave={onKpiSave} />)}</div>;
}

function KpiEditor({ kpi, onSave }: { kpi: Kra['kpis'][number]; onSave: (id: number, actual: number, notes: string) => Promise<void> }) {
  const [actual, setActual] = useState(kpi.actual_value ?? 0);
  const [notes, setNotes] = useState('');
  return <div style={styles.kpi}><span>{kpi.name}: target {kpi.target_value}, score {kpi.score ?? '—'}</span><div style={styles.controls}><input type="number" value={actual} onChange={(event) => setActual(Number(event.target.value))} aria-label={`Actual value for ${kpi.name}`} /><input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Measurement note" /><button type="button" className="secondary-action" onClick={() => void onSave(kpi.id, actual, notes)}>Submit actual</button></div></div>;
}

function Metric({ label, value }: { label: string; value: string | number }) { return <div><span style={styles.muted}>{label}</span><strong style={{ display: 'block', fontSize: '1.5rem' }}>{value}</strong></div>; }
const styles: Record<string, React.CSSProperties> = {
  header: { display: 'flex', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap', marginBottom: 18 },
  metrics: { display: 'flex', gap: 24, alignItems: 'center' }, grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 18 }, card: { marginBottom: 18 }, title: { marginTop: 0 }, item: { padding: 14, border: '1px solid #e2e8f0', borderRadius: 10, marginBottom: 10 }, controls: { display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }, muted: { color: '#64748b' }, error: { padding: 12, borderRadius: 10, background: '#fee2e2', color: '#991b1b' }, progressBar: { height: 7, background: '#e2e8f0', borderRadius: 5, overflow: 'hidden', margin: '10px 0' },     input: { border: '1px solid #cbd5e1', borderRadius: 8, padding: 8, minWidth: 90, flex: 1 }, addForm: { display: 'flex', gap: 8, marginBottom: 12 }, kpi: { marginTop: 10, padding: 10, background: '#f8fafc', borderRadius: 8 },
};
