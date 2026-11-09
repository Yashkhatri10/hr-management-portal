import { useEffect, useState } from 'react';
import { getAllProgressReports, reviewProgressReport, type ProgressReport } from '../services/api';
import { Layout } from '../components/Layout';

type Report = ProgressReport & { employee_id: number };

export function ProgressReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [statusFilter, setStatusFilter] = useState('All');
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState<Record<number, string>>({});

  const load = async () => {
    try {
      setReports((await getAllProgressReports()).reports);
      setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load progress reports.');
    }
  };
  useEffect(() => { void load(); }, []);
  const visible = statusFilter === 'All' ? reports : reports.filter((report) => report.status === statusFilter);

  const review = async (report: Report) => {
    try {
      await reviewProgressReport(report.id, 'Reviewed', feedback[report.id] || '');
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to review progress report.');
    }
  };

  return <Layout title="Progress reports" subtitle="HR review">
    {error && <p role="alert" style={styles.error}>{error}</p>}
    <div style={styles.toolbar}><label>Status <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option>All</option><option>Draft</option><option>Submitted</option><option>Under Review</option><option>Reviewed</option></select></label><span>{visible.length} report{visible.length === 1 ? '' : 's'}</span></div>
    <div style={styles.stack}>{visible.length === 0 ? <p>No progress reports match this filter.</p> : visible.map((report) => <article key={report.id} className="surface-card" style={styles.card}><div style={styles.row}><strong>Employee #{report.employee_id}</strong><span style={styles.status}>{report.status}</span></div><p style={styles.muted}>{report.period_type} · {report.period_start} to {report.period_end}</p><p>{report.summary}</p>{report.achievements && <p><strong>Achievements:</strong> {report.achievements}</p>}{report.blockers && <p><strong>Blockers:</strong> {report.blockers}</p>}{report.status !== 'Reviewed' && <div style={styles.review}><input value={feedback[report.id] || ''} onChange={(event) => setFeedback({ ...feedback, [report.id]: event.target.value })} placeholder="HR feedback" /><button type="button" className="primary-action" onClick={() => void review(report)}>Mark reviewed</button></div>}{report.review_feedback && <p style={styles.muted}>Existing feedback: {report.review_feedback}</p>}</article>)}</div>
  </Layout>;
}

const styles: Record<string, React.CSSProperties> = {
  toolbar: { display: 'flex', alignItems: 'center', gap: 18, marginBottom: 18, padding: 14, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12 },
  stack: { display: 'grid', gap: 14 }, card: { padding: 20 }, row: { display: 'flex', justifyContent: 'space-between', gap: 12 }, muted: { color: '#64748b' }, status: { padding: '5px 9px', borderRadius: 999, background: '#e0e7ff', color: '#3730a3', fontSize: '.8rem', fontWeight: 700 }, review: { display: 'flex', gap: 8 }, error: { padding: 12, borderRadius: 10, background: '#fee2e2', color: '#991b1b' },
};
