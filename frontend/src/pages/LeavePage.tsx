import { useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { cancelLeaveRequest, createLeaveRequest, getLeaveAllocationPreview, getLeaveRequests, getMyPaidLeaveBalance, updateLeaveStatus, type PaidLeaveRow } from '../services/api';
import type { LeaveRequest, User } from '../types';
import { getIndiaNationalHolidays } from '../utils/indiaNationalHolidays';

const weekdayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function dateKey(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function monthLabel(year: number, month: number): string {
  return new Intl.DateTimeFormat('en-IN', { month: 'long', timeZone: 'UTC' }).format(new Date(Date.UTC(year, month, 1)));
}

export function LeavePage({ user, onBalanceChanged }: { user: User; onBalanceChanged: () => Promise<void> }) {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [visibleYear, setVisibleYear] = useState(() => new Date().getFullYear());
  const [form, setForm] = useState({
    employee_name: user.name,
    employee_email: user.email,
    leave_type: 'Annual',
    start_date: new Date().toISOString().slice(0, 10),
    end_date: new Date().toISOString().slice(0, 10),
    reason: '',
    is_half_day: false,
  });
  const [paidBalance, setPaidBalance] = useState<PaidLeaveRow | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const response = await getLeaveRequests();
        setRequests(response.requests);
        const balance = await getMyPaidLeaveBalance();
        setPaidBalance(balance);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCancel = async (requestId: number) => {
    if (!window.confirm('Cancel this leave request? If it was approved, the paid leave debit will be reversed.')) return;
    setLoading(true);
    try {
      await cancelLeaveRequest(requestId);
      const [response, balance] = await Promise.all([getLeaveRequests(), getMyPaidLeaveBalance()]);
      setRequests(response.requests);
      setPaidBalance(balance);
      await onBalanceChanged();
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Unable to cancel leave request.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    if (!form.employee_email.trim() || !form.reason.trim()) {
      setError('Email and reason are required.');
      return;
    }
    if (form.end_date < form.start_date) {
      setError('End date must be on or after the start date.');
      return;
    }
    setLoading(true);
    try {
      await createLeaveRequest(form);
      const response = await getLeaveRequests();
      setRequests(response.requests);
      const balance = await getMyPaidLeaveBalance();
      setPaidBalance(balance);
      await onBalanceChanged();
      setForm((previous) => ({ ...previous, reason: '', is_half_day: false, end_date: previous.start_date }));
      setSuccess('Leave request submitted successfully.');
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to submit leave request.');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (requestId: number, status: 'Approved' | 'Rejected') => {
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      if (status === 'Approved') {
        const preview = await getLeaveAllocationPreview(requestId);
        const confirmed = window.confirm(`Approve ${preview.requested_days.toFixed(2)} days?\nPaid: ${preview.paid_days.toFixed(2)} days\nUnpaid: ${preview.unpaid_days.toFixed(2)} days\nAvailable paid balance: ${preview.available_paid_days.toFixed(2)} days`);
        if (!confirmed) return;
      }
      await updateLeaveStatus(requestId, status);
      const response = await getLeaveRequests();
      setRequests(response.requests);
      setPaidBalance(await getMyPaidLeaveBalance());
      await onBalanceChanged();
      setSuccess(`Leave request ${status.toLowerCase()} successfully.`);
    } catch (error) {
      setError(error instanceof Error ? error.message : `Unable to ${status.toLowerCase()} leave request.`);
    } finally {
      setLoading(false);
    }
  };

  const holidayByDate = new Map(getIndiaNationalHolidays(visibleYear).map((holiday) => [holiday.date, holiday.name]));
  const currentMonth = new Date().toISOString().slice(0, 7);
  const currentYear = currentMonth.slice(0, 4);
  const approvedRequests = requests.filter((request) => request.status === 'Approved');
  const currentMonthRequests = approvedRequests.filter((request) => request.start_date.slice(0, 7) === currentMonth);
  const unpaidThisMonth = currentMonthRequests.reduce((sum, request) => sum + (request.unpaid_days || 0), 0);
  const unpaidThisYear = approvedRequests
    .filter((request) => request.start_date.slice(0, 4) === currentYear)
    .reduce((sum, request) => sum + (request.unpaid_days || 0), 0);
  const carriedForward = Math.max(paidBalance?.opening_balance || 0, 0);
  const paidUsedThisMonth = currentMonthRequests.reduce((sum, request) => sum + (request.paid_days || 0), 0);
  const usageCapacity = Math.max(carriedForward + (paidBalance?.current_month_credit || paidBalance?.monthly_entitlement || 0), 0);
  const usagePercent = usageCapacity > 0 ? Math.min((paidUsedThisMonth / usageCapacity) * 100, 100) : 0;
  const months = Array.from({ length: 12 }, (_, month) => {
    const daysInMonth = new Date(Date.UTC(visibleYear, month + 1, 0)).getUTCDate();
    const firstWeekdayOffset = new Date(Date.UTC(visibleYear, month, 1)).getUTCDay();
    const cells: Array<number | null> = [
      ...Array.from({ length: firstWeekdayOffset }, () => null),
      ...Array.from({ length: daysInMonth }, (_, index) => index + 1),
    ];
    while (cells.length % 7 !== 0) cells.push(null);
    return { month, cells };
  });

  return (
    <Layout title="Leave" subtitle="Requests" actions={<a href="#leave-form" className="primary-action" style={styles.primaryButton}>New request</a>}>
      <section className="surface-card" style={styles.calendarCard} aria-label="Yearly leave and India national holiday calendar">
        <div style={styles.calendarHeader}>
          <div>
            <h3 style={styles.title}>Yearly leave calendar</h3>
            <p style={styles.calendarSubtitle}>India national holidays and employee leave</p>
          </div>
          <div style={styles.calendarControls}>
            <button type="button" aria-label="Previous year" style={styles.monthButton} onClick={() => setVisibleYear((year) => year - 1)}>‹</button>
            <strong style={styles.monthLabel}>{visibleYear}</strong>
            <button type="button" aria-label="Next year" style={styles.monthButton} onClick={() => setVisibleYear((year) => year + 1)}>›</button>
            <button type="button" style={styles.todayButton} onClick={() => {
              setVisibleYear(new Date().getFullYear());
            }}>This year</button>
          </div>
        </div>
        <div style={styles.legend}>
          <span><i style={{ ...styles.legendDot, background: '#dc2626' }} />India national holiday</span>
          <span><i style={{ ...styles.legendDot, background: '#4f46e5' }} />Approved leave</span>
          <span><i style={{ ...styles.legendDot, background: '#f59e0b' }} />Pending request</span>
        </div>
        <div className="calendar-year-grid" style={styles.yearGrid}>
          {months.map(({ month, cells }) => (
            <div key={month} className="calendar-month-card" style={styles.monthCard}>
              <h4 style={styles.monthTitle}>{monthLabel(visibleYear, month)}</h4>
              <div style={styles.monthGrid}>
                {weekdayLabels.map((weekday) => <div key={weekday} style={styles.miniWeekday}>{weekday.slice(0, 1)}</div>)}
                {cells.map((day, index) => {
                  if (day === null) return <div key={`empty-${month}-${index}`} style={styles.miniEmptyDay} />;
                  const key = dateKey(visibleYear, month, day);
                  const holiday = holidayByDate.get(key);
                  const dayRequests = requests.filter((request) => !['Rejected', 'Cancelled'].includes(request.status) && request.start_date <= key && request.end_date >= key);
                  const isToday = key === new Date().toISOString().slice(0, 10);
                  return (
                    <div key={key} className="calendar-mini-day" title={[holiday, ...dayRequests.map((request) => `${request.employee_name} — ${request.status}`)].filter(Boolean).join(' | ') || key} style={{ ...styles.miniDay, ...(holiday ? styles.holidayDay : {}), ...(dayRequests.length ? styles.leaveDay : {}), ...(isToday ? styles.todayDay : {}) }}>
                      {day}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        <div style={styles.holidayList}>
          <strong>India national holidays — {visibleYear}</strong>
          {Array.from(holidayByDate.entries()).map(([date, name]) => (
            <span key={date} style={styles.holidayListItem}>{new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(new Date(`${date}T00:00:00Z`))}: {name}</span>
          ))}
          <small style={styles.calendarSubtitle}>State and festival holidays vary by state and are not included in this national list.</small>
        </div>
      </section>
      {error && <p role="alert" className="error-banner" style={{ margin: '14px 0' }}>{error}</p>}
      {success && <p role="status" style={{ ...styles.success, margin: '14px 0' }}>{success}</p>}
      {paidBalance && <section style={styles.balanceSection} aria-label="Leave balance summary">
        <div style={styles.balanceHeader}><div><h3 style={styles.balanceTitle}>Paid leave balance</h3><p style={styles.balanceHint}>Your monthly allowance is separate from your accumulated available balance.</p></div><strong style={styles.availableValue}>{paidBalance.remaining_balance.toFixed(2)} days available</strong></div>
        <div style={styles.balanceCards}>
          <div style={styles.balanceCard}><span>Monthly allowance</span><strong>{paidBalance.monthly_entitlement.toFixed(2)} days</strong><small>Current policy</small></div>
          <div style={styles.balanceCard}><span>Carried forward</span><strong>{carriedForward.toFixed(2)} days</strong><small>Net balance from previous months</small></div>
          <div style={styles.balanceCard}><span>Paid used this month</span><strong>{paidUsedThisMonth.toFixed(2)} days</strong><small>Approved requests only</small></div>
          <div style={{ ...styles.balanceCard, ...styles.balanceCardPrimary }}><span>Total available balance</span><strong>{paidBalance.remaining_balance.toFixed(2)} days</strong><small>Never replaced by monthly allowance</small></div>
        </div>
        <div style={styles.progressWrap}><div style={styles.progressLabel}><span>Current-month paid leave usage</span><strong>{paidUsedThisMonth.toFixed(2)} / {usageCapacity.toFixed(2)} days</strong></div><div style={styles.progressTrack}><div style={{ ...styles.progressBar, width: `${usagePercent}%` }} /></div></div>
      </section>}
      <section style={styles.unpaidSection} aria-label="Unpaid leave">
        <div style={styles.balanceHeader}><div><h3 style={styles.balanceTitle}>Unpaid leave</h3><p style={styles.balanceHint}>Only approved unpaid allocations are included.</p></div><strong style={styles.unpaidValue}>{unpaidThisMonth.toFixed(2)} days this month</strong></div>
        <div style={styles.unpaidSummary}><div><span>Current month</span><strong>{unpaidThisMonth.toFixed(2)} days</strong></div><div><span>Selected year</span><strong>{unpaidThisYear.toFixed(2)} days</strong></div></div>
        <div style={styles.unpaidHistory}>{approvedRequests.filter((request) => (request.unpaid_days || 0) > 0).length === 0 ? <p style={styles.emptyText}>No unpaid leave has been allocated.</p> : approvedRequests.filter((request) => (request.unpaid_days || 0) > 0).map((request) => <div key={request.id} style={styles.unpaidItem}><div><strong>{request.start_date}{request.start_date !== request.end_date ? ` to ${request.end_date}` : ''}</strong><small>{request.leave_type} · {request.status}</small></div><strong>{(request.unpaid_days || 0).toFixed(2)} days unpaid</strong></div>)}</div>
      </section>
      <div style={styles.grid}>
        <form id="leave-form" onSubmit={handleSubmit} className="surface-card" style={styles.card}>
          <h3 style={styles.title}>Apply for leave</h3>
          <p style={styles.calendarSubtitle}>Paid leave usage counts weekdays and excludes Republic Day, Independence Day and Gandhi Jayanti. Other leave types follow HR policy.</p>

          <div style={styles.fieldRow}>
            <label style={styles.label}>Employee name</label>
            <input value={form.employee_name} onChange={(e) => handleChange('employee_name', e.target.value)} style={styles.input} />
          </div>

          <div style={styles.fieldRow}>
            <label style={styles.label}>Email</label>
            <input type="email" required value={form.employee_email} onChange={(e) => handleChange('employee_email', e.target.value)} style={styles.input} />
          </div>

          <div style={styles.fieldRow}>
            <label style={styles.label}>Leave type</label>
            <select value={form.leave_type} onChange={(e) => handleChange('leave_type', e.target.value)} style={styles.input}>
              <option>Paid Leave</option>
              <option>Annual</option>
              <option>Unpaid</option>
              <option>Sick</option>
              <option>Parental</option>
              <option>Study</option>
            </select>
          </div>

          <label style={styles.halfDayLabel}><input type="checkbox" checked={form.is_half_day} onChange={(e) => setForm((prev) => ({ ...prev, is_half_day: e.target.checked, end_date: e.target.checked ? prev.start_date : prev.end_date }))} /> Request half-day leave</label>

          <div style={styles.twoCol}>
            <div style={styles.fieldRow}>
              <label style={styles.label}>Start date</label>
              <input type="date" value={form.start_date} onChange={(e) => setForm((prev) => ({ ...prev, start_date: e.target.value, ...(prev.is_half_day ? { end_date: e.target.value } : {}) }))} style={styles.input} />
            </div>
            <div style={styles.fieldRow}>
              <label style={styles.label}>End date</label>
              <input type="date" min={form.start_date} disabled={form.is_half_day} value={form.end_date} onChange={(e) => handleChange('end_date', e.target.value)} style={styles.input} />
            </div>
          </div>

          <div style={styles.fieldRow}>
            <label style={styles.label}>Reason</label>
            <textarea required minLength={1} value={form.reason} onChange={(e) => handleChange('reason', e.target.value)} style={{ ...styles.input, minHeight: '90px', resize: 'vertical' }} />
          </div>

          <button type="submit" style={styles.primaryButton} disabled={loading}>
            {loading ? 'Submitting...' : 'Submit leave request'}
          </button>
        </form>

        <div className="surface-card" style={styles.card}>
          <h3 style={styles.title}>Recent requests</h3>
          <div style={styles.list}>
            {requests.length === 0 ? (
              <p>No leave requests yet.</p>
            ) : (
              requests.map((request) => (
                <div key={request.id} style={styles.requestItem}>
                  <div style={styles.requestHeader}>
                    <strong>{request.employee_name}</strong>
                    <span style={{ ...styles.statusPill, background: request.status === 'Approved' ? '#dcfce7' : request.status === 'Rejected' ? '#fee2e2' : request.status === 'Cancelled' ? '#e2e8f0' : '#fef3c7', color: request.status === 'Approved' ? '#166534' : request.status === 'Rejected' ? '#991b1b' : request.status === 'Cancelled' ? '#334155' : '#92400e' }}>
                      {request.status}
                    </span>
                  </div>
                  <div style={styles.meta}>{request.leave_type} • {request.start_date} to {request.end_date}</div>
                  {request.is_half_day && <div style={styles.meta}>Half day (0.50 days)</div>}
                  <div style={styles.meta}>{request.reason}</div>
                  {request.status === 'Approved' && <div style={styles.allocation}>Total: {((request.paid_days || 0) + (request.unpaid_days || 0)).toFixed(2)} days · Paid: {(request.paid_days || 0).toFixed(2)} · Unpaid: {(request.unpaid_days || 0).toFixed(2)}</div>}
                  {request.status === 'Pending' && user.role === 'HR Manager' && (
                    <div style={styles.actionRow}>
                      <button type="button" disabled={loading} onClick={() => void handleStatusChange(request.id, 'Approved')} style={{ ...styles.actionButton, background: '#16a34a', color: '#fff' }}>
                        Approve
                      </button>
                      <button type="button" disabled={loading} onClick={() => void handleStatusChange(request.id, 'Rejected')} style={{ ...styles.actionButton, background: '#ef4444', color: '#fff' }}>
                        Reject
                      </button>
                    </div>
                  )}
                  {(request.status === 'Pending' || request.status === 'Approved') && <button type="button" disabled={loading} onClick={() => handleCancel(request.id)} style={styles.cancelRequestButton}>Cancel request</button>}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

const styles: Record<string, React.CSSProperties> = {
  success: { padding: '12px', borderRadius: '10px', background: '#e5f8ef', color: '#17623e' },
  balanceSection: { padding: '22px', marginBottom: '16px', border: '1px solid #dbe5f0', borderRadius: '18px', background: '#fff', color: '#18304b' },
  balanceHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' },
  balanceTitle: { margin: 0, fontSize: '1.1rem', color: '#172b46' },
  balanceHint: { margin: '5px 0 0', color: '#64748b', fontSize: '.82rem' },
  availableValue: { color: '#176b60', fontSize: '1.25rem' },
  balanceCards: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px', marginTop: '18px' },
  balanceCard: { display: 'flex', flexDirection: 'column', gap: '6px', padding: '15px', borderRadius: '12px', background: '#f7f9fc', color: '#526681' },
  balanceCardPrimary: { background: '#eefaf7', color: '#176b60' },
  progressWrap: { marginTop: '18px' },
  progressLabel: { display: 'flex', justifyContent: 'space-between', gap: '10px', color: '#526681', fontSize: '.78rem', marginBottom: '7px' },
  progressTrack: { height: '9px', borderRadius: '999px', background: '#e6edf5', overflow: 'hidden' },
  progressBar: { height: '100%', borderRadius: '999px', background: 'linear-gradient(90deg, #10b981, #4f46e5)', transition: 'width .2s ease' },
  unpaidSection: { padding: '22px', marginBottom: '20px', border: '1px solid #eadfd1', borderRadius: '18px', background: '#fffaf4' },
  unpaidValue: { color: '#a15c17', fontSize: '1.1rem' },
  unpaidSummary: { display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '16px' },
  unpaidSummaryBox: { padding: '12px 16px', borderRadius: '10px', background: '#fff1dc' },
  unpaidHistory: { display: 'grid', gap: '8px', marginTop: '14px' },
  unpaidItem: { display: 'flex', justifyContent: 'space-between', gap: '12px', padding: '12px 14px', borderRadius: '10px', background: '#fff', color: '#754619' },
  allocation: { marginTop: '8px', color: '#536b87', fontWeight: 700, fontSize: '.78rem' },
  emptyText: { color: '#64748b', fontSize: '.85rem' },
  balanceLabel: { display: 'block', color: '#5a6d87', fontSize: '.75rem', fontWeight: 700, marginBottom: '5px' },
  balanceValue: { display: 'block', color: '#176b60', fontSize: '1.35rem' },
  halfDayLabel: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: '#354963', fontSize: '.85rem', fontWeight: 700 },
  cancelRequestButton: { marginTop: '10px', border: '1px solid #f3b7b7', borderRadius: '9px', padding: '7px 10px', background: '#fff1f2', color: '#9f2525', fontSize: '.75rem', fontWeight: 700, cursor: 'pointer' },
  calendarCard: {
    background: '#fff',
    borderRadius: '20px',
    padding: '22px',
    border: '1px solid #e2e8f0',
    marginBottom: '20px',
  },
  calendarHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '16px',
    flexWrap: 'wrap',
  },
  calendarSubtitle: { margin: '-8px 0 0', color: '#64748b', fontSize: '0.86rem' },
  calendarControls: { display: 'flex', alignItems: 'center', gap: '10px' },
  monthLabel: { minWidth: '150px', textAlign: 'center', color: '#0f172a' },
  monthButton: {
    border: '1px solid #e2e8f0',
    background: '#fff',
    borderRadius: '10px',
    width: '36px',
    height: '36px',
    fontSize: '1.4rem',
    color: '#334155',
    cursor: 'pointer',
  },
  todayButton: { border: '1px solid #c7d2fe', background: '#eef2ff', color: '#4338ca', borderRadius: '10px', padding: '9px 12px', fontWeight: 700, cursor: 'pointer' },
  legend: { display: 'flex', gap: '18px', flexWrap: 'wrap', margin: '18px 0 12px', color: '#475569', fontSize: '0.78rem' },
  legendDot: { display: 'inline-block', width: '9px', height: '9px', borderRadius: '50%', marginRight: '7px' },
  yearGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '14px' },
  monthCard: { minWidth: 0, padding: '12px', border: '1px solid #e2e8f0', borderRadius: '14px', background: '#fff' },
  monthTitle: { margin: '0 0 8px', textAlign: 'center', color: '#1e293b', fontSize: '0.92rem' },
  monthGrid: { display: 'grid', gridTemplateColumns: 'repeat(7, minmax(0, 1fr))', gap: '3px' },
  miniWeekday: { textAlign: 'center', padding: '4px 0', color: '#94a3b8', fontSize: '0.62rem', fontWeight: 700 },
  miniEmptyDay: { aspectRatio: '1', minWidth: 0 },
  miniDay: { aspectRatio: '1', minWidth: 0, display: 'grid', placeItems: 'center', borderRadius: '50%', color: '#334155', fontSize: '0.7rem' },
  holidayDay: { background: '#fee2e2', color: '#991b1b', fontWeight: 800 },
  leaveDay: { outline: '2px solid #6366f1', outlineOffset: '-2px' },
  todayDay: { boxShadow: 'inset 0 0 0 2px #0f172a', fontWeight: 800 },
  holidayList: { display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', marginTop: '18px', paddingTop: '14px', borderTop: '1px solid #e2e8f0', color: '#334155', fontSize: '0.8rem' },
  holidayListItem: { padding: '6px 9px', borderRadius: '8px', background: '#fff1f2', color: '#9f1239' },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1.2fr 1fr',
    gap: '20px',
  },
  card: {
    background: '#fff',
    borderRadius: '20px',
    padding: '22px',
    border: '1px solid #e2e8f0',
  },
  title: {
    marginTop: 0,
    marginBottom: '16px',
    fontSize: '1.3rem',
  },
  fieldRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    marginBottom: '14px',
  },
  label: {
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#475569',
  },
  input: {
    border: '1px solid #dbe2f0',
    borderRadius: '12px',
    padding: '12px 14px',
    fontSize: '0.95rem',
    background: '#f8fafc',
  },
  twoCol: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '14px',
  },
  primaryButton: {
    border: 'none',
    borderRadius: '12px',
    padding: '12px 16px',
    background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
    color: '#fff',
    fontWeight: 700,
    cursor: 'pointer',
    textDecoration: 'none',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  requestItem: {
    border: '1px solid #e2e8f0',
    borderRadius: '14px',
    padding: '12px 14px',
    background: '#f8fafc',
  },
  requestHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '8px',
    marginBottom: '8px',
  },
  meta: {
    color: '#475569',
    fontSize: '0.82rem',
    marginBottom: '4px',
  },
  statusPill: {
    padding: '4px 8px',
    borderRadius: '999px',
    fontSize: '0.7rem',
    fontWeight: 700,
  },
  actionRow: {
    display: 'flex',
    gap: '8px',
    marginTop: '12px',
  },
  actionButton: {
    border: 'none',
    borderRadius: '10px',
    padding: '8px 12px',
    fontWeight: 700,
    cursor: 'pointer',
  },
};
