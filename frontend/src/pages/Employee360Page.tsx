import { useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { addEmployeeActivity, addEmployeeKra, addEmployeeReview, addEmployeeTask, downloadReport, getEmployee360, getEmployeeProgressReports, type Employee360Data, type ProgressReport } from '../services/api';
import type { Employee } from '../types';

type Props = { employee: Employee; onBack: () => void };
type Tab = 'overview' | 'activities' | 'tasks' | 'kra' | 'reviews';

export function Employee360Page({ employee, onBack }: Props) {
  const [data, setData] = useState<Employee360Data | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [reports, setReports] = useState<ProgressReport[]>([]);
  const [error, setError] = useState('');
  const [formValue, setFormValue] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setError('');
    Promise.all([getEmployee360(employee.id), getEmployeeProgressReports(employee.id)]).then(([profile, reportResponse]) => {
      setData(profile);
      setReports(reportResponse.reports);
    }).catch((reason) => {
      setError(reason instanceof Error ? reason.message : 'Unable to load employee profile.');
    });
  }, [employee.id]);

  if (error) {
    return <Layout title="Employee 360°" subtitle="Profile"><p role="alert" style={styles.error}>{error}</p><button type="button" onClick={onBack}>Back to employees</button></Layout>;
  }
  if (!data) return <div className="loading-screen">Loading employee profile...</div>;
  const refresh = () => getEmployee360(employee.id).then(setData);
  const submitRecord = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formValue.trim()) return;
    setSaving(true);
    try {
      if (tab === 'activities') await addEmployeeActivity(employee.id, { title: formValue, activity_type: 'work update' });
      if (tab === 'tasks') await addEmployeeTask(employee.id, { title: formValue, priority: 'Medium' });
      if (tab === 'kra') await addEmployeeKra(employee.id, { title: formValue, weight: 1, period_start: new Date().toISOString().slice(0, 10), period_end: `${new Date().getFullYear()}-12-31` });
      if (tab === 'reviews') await addEmployeeReview(employee.id, { review_period: new Date().toISOString().slice(0, 7), comments: formValue });
      setFormValue('');
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to save this record.');
    } finally {
      setSaving(false);
    }
  };

  const tabs: Array<[Tab, string]> = [['overview', 'Overview'], ['activities', 'Activities'], ['tasks', 'Tasks'], ['kra', 'KRA / KPI'], ['reviews', 'Reviews']];
  return (
    <Layout title={data.employee.name} subtitle="Employee 360° profile" actions={<div style={{ display: 'flex', gap: 8 }}><button type="button" className="secondary-action" onClick={() => void downloadReport('employee-360', 'csv', { employee_id: employee.id })}>CSV</button><button type="button" className="secondary-action" onClick={() => void downloadReport('employee-360', 'xlsx', { employee_id: employee.id })}>Excel</button><button type="button" className="secondary-action" onClick={() => void downloadReport('employee-360', 'pdf', { employee_id: employee.id })}>PDF</button><button type="button" className="secondary-action" onClick={onBack}>Back to employees</button></div>}>
      <section className="surface-card" style={styles.header}>
        <div><h2 style={{ margin: 0 }}>{data.employee.name}</h2><p style={styles.muted}>{data.employee.role} · {data.employee.department} · {data.employee.email}</p><p style={styles.muted}>Manager: {data.employee.manager || 'Not assigned'} · Status: {data.employee.status}</p></div>
        <div style={styles.metrics}><Metric label="Open tasks" value={data.summary.open_tasks} /><Metric label="Completed" value={data.summary.completed_tasks} /><Metric label="Overdue" value={data.summary.overdue_tasks ?? 0} /><Metric label="KPI score" value={data.summary.average_kpi_score ?? '—'} /></div>
      </section>
      <nav style={styles.tabs} aria-label="Employee profile sections">{tabs.map(([key, label]) => <button type="button" key={key} onClick={() => setTab(key)} style={{ ...styles.tab, ...(tab === key ? styles.activeTab : {}) }}>{label}</button>)}</nav>
      {tab === 'overview' && <div style={styles.grid}><Card title="Professional details"><Row label="Employee ID" value={data.employee.id} /><Row label="Email" value={data.employee.email} /><Row label="Designation" value={data.employee.role} /><Row label="Department" value={data.employee.department} /><Row label="Reporting manager" value={data.employee.manager || 'Not assigned'} /></Card><Card title="Performance snapshot"><Row label="KRAs" value={data.summary.kra_count} /><Row label="KPIs" value={data.summary.kpi_count} /><Row label="Average review score" value={data.summary.average_review_score ?? 'Not reviewed'} /><Row label="Recent activities" value={data.activities.length} /></Card></div>}
      {tab === 'activities' && <List items={data.activities.map((item) => `${item.activity_date} · ${item.title} — ${item.description || item.activity_type}`)} empty="No documented activities yet." />}
      {tab === 'tasks' && <List items={data.tasks.map((item) => `${item.title} · ${item.status} · ${item.priority}${item.due_date ? ` · due ${item.due_date}` : ''}${item.overdue ? ' · OVERDUE' : ''}`)} empty="No assigned tasks yet." />}
      {tab === 'kra' && <div style={styles.stack}>{data.kras.length === 0 ? <p>No KRAs assigned yet.</p> : data.kras.map((kra) => <Card key={kra.id} title={`${kra.title} (${kra.weight} weight)`}><p style={styles.muted}>{kra.description || 'No description'} · {kra.period_start} to {kra.period_end}</p>{kra.kpis.map((kpi) => <Row key={kpi.id} label={kpi.name} value={`${kpi.actual_value ?? '—'} / ${kpi.target_value}${kpi.unit ? ` ${kpi.unit}` : ''} · score ${kpi.score ?? '—'}`} />)}</Card>)}</div>}
      {tab === 'reviews' && <List items={data.reviews.map((review) => `${review.review_period} · ${review.review_type} · ${review.status} · score ${review.overall_score ?? '—'}${review.comments ? ` — ${review.comments}` : ''}`)} empty="No performance reviews yet." />}
      {tab === 'overview' && <div style={styles.grid}><Card title="Attendance and leave"><Row label="Attendance rate" value={`${data.attendance?.attendance_rate ?? 0}%`} /><Row label="Present days" value={data.attendance?.present ?? 0} /><Row label="Leave requests" value={data.leave?.request_count ?? 0} /><Row label="Approved leave days" value={data.leave?.approved_days ?? 0} /></Card><Card title="Goals and development"><List items={(data.goals || []).map((goal) => `${goal.title} · ${goal.status} · ${goal.progress_percentage}%`)} empty="No goals recorded." /></Card></div>}
      {tab === 'overview' && <Card title="Documents and certifications"><List items={(data.documents || []).map((document) => `${document.title} · ${document.document_type}${document.expiry_date ? ` · expires ${document.expiry_date}` : ''}`)} empty="No document metadata recorded." /></Card>}
      <section className="surface-card" style={styles.card}><h3 style={{ marginTop: 0 }}>Progress reports</h3>{reports.length === 0 ? <p>No progress reports submitted.</p> : reports.map((report) => <div key={report.id} style={styles.item}><strong>{report.period_type} · {report.period_start} to {report.period_end}</strong><span style={styles.muted}> · {report.status}</span><p>{report.summary}</p>{report.achievements && <p>Achievements: {report.achievements}</p>}{report.blockers && <p>Blockers: {report.blockers}</p>}{report.review_feedback && <p style={styles.muted}>HR feedback: {report.review_feedback}</p>}</div>)}</section>
      {tab !== 'overview' && <form onSubmit={(event) => void submitRecord(event)} style={styles.addForm}><input required value={formValue} onChange={(event) => setFormValue(event.target.value)} placeholder={`Add ${tab === 'kra' ? 'KRA' : tab === 'reviews' ? 'review note' : tab.slice(0, -1)}`} style={styles.input} /><button type="submit" className="primary-action" disabled={saving}>{saving ? 'Saving…' : 'Add record'}</button></form>}
    </Layout>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) { return <div><span style={styles.muted}>{label}</span><strong style={{ display: 'block', fontSize: '1.5rem' }}>{value}</strong></div>; }
function Card({ title, children }: { title: string; children: React.ReactNode }) { return <section className="surface-card" style={styles.card}><h3 style={{ marginTop: 0 }}>{title}</h3>{children}</section>; }
function Row({ label, value }: { label: string; value: string | number }) { return <div style={styles.row}><span style={styles.muted}>{label}</span><strong>{value}</strong></div>; }
function List({ items, empty }: { items: string[]; empty: string }) { return <Card title="Records">{items.length ? <div style={styles.stack}>{items.map((item, index) => <div key={`${item}-${index}`} style={styles.item}>{item}</div>)}</div> : <p>{empty}</p>}</Card>; }

const styles: Record<string, React.CSSProperties> = {
  header: { display: 'flex', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap', marginBottom: 18 },
  metrics: { display: 'flex', gap: 24, alignItems: 'center' },
  tabs: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 },
  tab: { border: '1px solid #dbe2f0', borderRadius: 10, padding: '10px 14px', background: '#fff', cursor: 'pointer', fontWeight: 700 },
  activeTab: { background: '#4f46e5', color: '#fff', borderColor: '#4f46e5' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 18 },
  card: { marginBottom: 18 },
  stack: { display: 'grid', gap: 10 },
  item: { padding: 14, border: '1px solid #e2e8f0', borderRadius: 10, background: '#f8fafc' },
  row: { display: 'flex', justifyContent: 'space-between', gap: 16, padding: '10px 0', borderBottom: '1px solid #eef2f7' },
  muted: { color: '#64748b' },
  error: { padding: 14, borderRadius: 10, background: '#fee2e2', color: '#991b1b' },
  addForm: { display: 'flex', gap: 10, marginTop: 18 },
  input: { flex: 1, border: '1px solid #dbe2f0', borderRadius: 10, padding: '11px 12px', fontSize: '0.95rem' },
};
