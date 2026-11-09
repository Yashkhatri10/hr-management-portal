import { Layout } from '../components/Layout';
import { downloadReport } from '../services/api';
import type { DashboardData } from '../types';
import { useState } from 'react';

type DashboardPageProps = {
  data: DashboardData;
};

export function DashboardPage({ data }: DashboardPageProps) {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');
  const summaryCards = [
    { label: 'Total employees', value: data.summary.totalEmployees },
    { label: 'Open positions', value: data.summary.openPositions },
    { label: 'Attendance', value: `${data.summary.attendance}%` },
    { label: 'Pending tasks', value: data.summary.pendingTasks },
    { label: 'Leave balance', value: `${data.summary.leaveBalance} days` },
    { label: 'Upcoming leaves', value: data.summary.upcomingLeaves },
  ];

  const exportDirectory = async () => {
    setExporting(true);
    setExportError('');
    try {
      await downloadReport('employees', 'xlsx');
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Unable to export the employee report.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <Layout
      title="Dashboard"
      subtitle="Overview"
      actions={<button type="button" className="primary-action" style={styles.primaryButton} disabled={exporting} onClick={() => void exportDirectory()}>
        {exporting ? 'Exporting…' : 'Export report'}
      </button>}
    >
      {exportError && <p role="alert" className="error-banner" style={{ margin: '0 0 18px' }}>{exportError}</p>}
      <section className="dashboard-hero">
        <div>
          <span className="dashboard-hero-kicker">People operations overview</span>
          <h2>Good to see you again.</h2>
          <p>Here is what is happening across your workforce today.</p>
        </div>
        <div className="dashboard-hero-mark" aria-hidden="true">✦</div>
      </section>
      <section className="dashboard-cards" style={styles.summaryGrid}>
        {summaryCards.map((card) => (
          <div key={card.label} className="dashboard-card" style={styles.summaryCard}>
            <span className="dashboard-card-label" style={styles.cardLabel}>{card.label}</span>
            <strong className="dashboard-card-value" style={styles.cardValue}>{card.value}</strong>
          </div>
        ))}
      </section>

      <section className="dashboard-content" style={styles.contentGrid}>
        <div className="surface-card dashboard-panel" style={styles.panel}>
          <h3 className="dashboard-panel-title" style={styles.panelTitle}>Recent activity</h3>
          {data.recentActivity.length === 0 ? <p style={styles.emptyState}>No recent activity recorded yet.</p> : (
            <ul style={styles.list}>
              {data.recentActivity.map((item) => <li key={item} style={styles.listItem}>{item}</li>)}
            </ul>
          )}
        </div>

        <div className="surface-card dashboard-panel" style={styles.panel}>
          <h3 className="dashboard-panel-title" style={styles.panelTitle}>Upcoming hires</h3>
          {data.upcomingHires.length === 0 ? <p style={styles.emptyState}>No upcoming hires recorded.</p> : (
            <ul style={styles.list}>
              {data.upcomingHires.map((item) => <li key={item} style={styles.listItem}>{item}</li>)}
            </ul>
          )}
        </div>
      </section>

      <section className="dashboard-content" style={{ ...styles.contentGrid, marginTop: '18px' }}>
        <div className="surface-card dashboard-panel" style={styles.panel}>
          <h3 className="dashboard-panel-title" style={styles.panelTitle}>Leave summary</h3>
          <ul style={styles.list}>
            <li style={styles.listItem}>Used leaves: {data.summary.usedLeaves} days</li>
            <li style={styles.listItem}>Leaves left: {data.summary.leaveBalance} days</li>
            <li style={styles.listItem}>Upcoming leave requests: {data.summary.upcomingLeaves}</li>
          </ul>
        </div>

        <div className="surface-card dashboard-panel" style={styles.panel}>
          <h3 className="dashboard-panel-title" style={styles.panelTitle}>Upcoming leave calendar</h3>
          <ul style={styles.list}>
            {data.upcomingLeaveSchedule.length === 0 ? (
              <li style={styles.listItem}>No upcoming leave planned.</li>
            ) : (
              data.upcomingLeaveSchedule.map((item) => (
                <li key={item} style={styles.listItem}>{item}</li>
              ))
            )}
          </ul>
        </div>
      </section>
    </Layout>
  );
}

const styles: Record<string, React.CSSProperties> = {
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  summaryCard: {
    background: '#fff',
    borderRadius: '18px',
    padding: '20px',
    border: '1px solid #e2e8f0',
    boxShadow: '0 10px 20px rgba(15, 23, 42, 0.04)',
  },
  cardLabel: {
    display: 'block',
    fontSize: '0.8rem',
    color: '#64748b',
  },
  cardValue: {
    display: 'block',
    marginTop: '8px',
    fontSize: '1.9rem',
  },
  contentGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: '18px',
  },
  panel: {
    background: '#fff',
    borderRadius: '18px',
    padding: '20px',
    border: '1px solid #e2e8f0',
  },
  panelTitle: {
    margin: '0 0 16px',
    fontSize: '1.2rem',
  },
  list: {
    margin: 0,
    paddingLeft: '20px',
    color: '#334155',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  listItem: {
    lineHeight: 1.6,
  },
  emptyState: { margin: 0, color: '#64748b', fontSize: '0.9rem' },
  primaryButton: {
    background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
    color: '#fff',
    border: 'none',
    borderRadius: '12px',
    padding: '12px 16px',
    fontWeight: 700,
    cursor: 'pointer',
  },
};
