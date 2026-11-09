import { useEffect, useMemo, useState } from 'react';
import { Layout } from '../components/Layout';
import {
  addPaidLeaveAdjustment,
  getPaidLeaveEmployeeDetails,
  getPaidLeavePolicy,
  getPaidLeaveReport,
  updatePaidLeavePolicy,
  type PaidLeaveEmployeeDetails,
  type PaidLeavePolicy,
  type PaidLeaveReport,
  type PaidLeaveReportFilters,
  type PaidLeaveRow,
} from '../services/api';

function currentPeriod(type: PaidLeaveReportFilters['periodType']): string {
  const now = new Date();
  if (type === 'month') return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  if (type === 'quarter') return `${now.getFullYear()}-Q${Math.floor(now.getMonth() / 3) + 1}`;
  const startYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
  return `${startYear}-${String(startYear + 1).slice(-2)}`;
}

function csvCell(value: unknown): string {
  const rawText = String(value ?? '');
  const text = /^[=+\-@\t\r]/.test(rawText) ? `'${rawText}` : rawText;
  return `"${text.replace(/"/g, '""')}"`;
}

function badge(status: string): React.CSSProperties {
  if (status === 'Probation') return { background: '#fff4d6', color: '#885300' };
  if (status === 'Regular') return { background: '#e3f7ed', color: '#17623e' };
  return { background: '#e2e8f0', color: '#334155' };
}

export function PaidLeavePage({ onChanged }: { onChanged: () => Promise<void> }) {
  const [periodType, setPeriodType] = useState<PaidLeaveReportFilters['periodType']>('month');
  const [period, setPeriod] = useState(() => currentPeriod('month'));
  const [search, setSearch] = useState('');
  const [department, setDepartment] = useState('');
  const [designation, setDesignation] = useState('');
  const [probationStatus, setProbationStatus] = useState('');
  const [employmentStatus, setEmploymentStatus] = useState('');
  const [sortBy, setSortBy] = useState<PaidLeaveReportFilters['sortBy']>('employee_name');
  const [report, setReport] = useState<PaidLeaveReport | null>(null);
  const [policy, setPolicy] = useState<PaidLeavePolicy | null>(null);
  const [details, setDetails] = useState<PaidLeaveEmployeeDetails | null>(null);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null);
  const [showPolicy, setShowPolicy] = useState(false);
  const [showAdjustment, setShowAdjustment] = useState(false);
  const [adjustment, setAdjustment] = useState({ amount: 0, effective_date: new Date().toISOString().slice(0, 10), reason: '' });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadReport = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await getPaidLeaveReport({ periodType, period, search, department, designation, probationStatus, employmentStatus, sortBy });
      setReport(response);
      if (selectedEmployeeId !== null && !response.employees.some((item) => item.employee_id === selectedEmployeeId)) {
        setSelectedEmployeeId(null);
        setDetails(null);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load the paid leave report.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadReport(); }, [periodType, period, search, department, designation, probationStatus, employmentStatus, sortBy]);
  useEffect(() => { getPaidLeavePolicy().then(setPolicy).catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Unable to load leave policy.')); }, []);

  useEffect(() => {
    if (selectedEmployeeId === null) return;
    getPaidLeaveEmployeeDetails(selectedEmployeeId, periodType, period)
      .then(setDetails)
      .catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Unable to load employee leave history.'));
  }, [selectedEmployeeId, periodType, period, report]);

  const departments = useMemo(() => Array.from(new Set(report?.employees.map((row) => row.department) ?? [])).sort(), [report]);
  const designations = useMemo(() => Array.from(new Set(report?.employees.map((row) => row.designation) ?? [])).sort(), [report]);
  const totals = useMemo(() => ({
    available: report?.employees.filter((row) => row.remaining_balance > 0).length ?? 0,
    overdrawn: report?.employees.filter((row) => row.remaining_balance <= 0).length ?? 0,
    taken: report?.employees.reduce((sum, row) => sum + row.period_taken, 0) ?? 0,
    unpaid: report?.employees.reduce((sum, row) => sum + row.period_unpaid, 0) ?? 0,
    pending: report?.employees.reduce((sum, row) => sum + row.pending_requests, 0) ?? 0,
  }), [report]);

  const changePeriodType = (type: PaidLeaveReportFilters['periodType']) => {
    setPeriodType(type);
    setPeriod(currentPeriod(type));
  };

  const exportCsv = () => {
    const rows: Array<Array<unknown>> = [
      ['Employee ID', 'Employee name', 'Email', 'Department', 'Designation', 'Joining date', 'Employment eligibility', 'Employee status', 'Monthly entitlement', 'Current month credit', 'Opening balance', 'Total credited', 'Manual adjustments', 'Paid leave used', 'Unpaid leave used (period)', 'Remaining balance', 'Pending requests', 'Utilization %'],
      ...(report?.employees ?? []).map((row: PaidLeaveRow) => [row.employee_id, row.employee_name, row.email, row.department, row.designation, row.date_of_joining, row.employment_status, row.employee_status, row.monthly_entitlement, row.current_month_credit, row.opening_balance, row.total_credited, row.manual_adjustments, row.total_taken, row.period_unpaid, row.remaining_balance, row.pending_requests, row.utilization_percent]),
    ];
    const blob = new Blob([rows.map((row) => row.map(csvCell).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `paid-leave-${report?.period || 'report'}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const savePolicy = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!policy) return;
    setSaving(true);
    setError('');
    try {
      const updated = await updatePaidLeavePolicy({
        probation_days: Number(policy.probation_days),
        probation_monthly_days: Number(policy.probation_monthly_days),
        regular_monthly_days: Number(policy.regular_monthly_days),
        paid_leave_types: policy.paid_leave_types,
        allow_negative_balance: policy.allow_negative_balance,
      });
      setPolicy(updated);
      setShowPolicy(false);
      setNotice(`Policy saved; new rules take effect ${updated.effective_from}. Existing monthly credits remain in the audit ledger.`);
      await loadReport();
      await onChanged();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to save the policy.');
    } finally {
      setSaving(false);
    }
  };

  const saveAdjustment = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedEmployeeId) return;
    setSaving(true);
    setError('');
    try {
      await addPaidLeaveAdjustment(selectedEmployeeId, adjustment);
      setNotice('Audited balance adjustment recorded.');
      setAdjustment({ ...adjustment, amount: 0, reason: '' });
      setShowAdjustment(false);
      await loadReport();
      setDetails(await getPaidLeaveEmployeeDetails(selectedEmployeeId, periodType, period));
      await onChanged();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to save adjustment.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout className="paid-leave-page" title="Paid leave" subtitle="Entitlements and balances" actions={
      <div style={styles.headerActions}>
        <button type="button" className="secondary-action" onClick={exportCsv}>Export CSV</button>
        <button type="button" className="secondary-action" onClick={() => window.print()}>Export PDF</button>
        <button type="button" className="primary-action" onClick={() => setShowPolicy((value) => !value)}>Leave policy</button>
      </div>
    }>
      {error && <div role="alert" className="error-banner" style={styles.notice}>{error}</div>}
      {notice && <div role="status" style={styles.success}>{notice}</div>}

      {showPolicy && policy && <form className="surface-card paid-leave-policy-panel" onSubmit={savePolicy} style={styles.policyPanel}>
        <div style={styles.sectionHeader}><div><h3 style={styles.title}>Paid leave policy</h3><p style={styles.muted}>Policy edits take effect from the first day of next month.</p></div><button type="button" className="secondary-action" onClick={() => setShowPolicy(false)}>Close</button></div>
        <div style={styles.policyGrid}>
          <label style={styles.label}>Probation duration (days)<input type="number" min={0} max={730} required value={policy.probation_days} style={styles.input} onChange={(event) => setPolicy({ ...policy, probation_days: Number(event.target.value) })} /></label>
          <label style={styles.label}>Probation leave / month<input type="number" min="0.01" step="0.01" required value={policy.probation_monthly_days} style={styles.input} onChange={(event) => setPolicy({ ...policy, probation_monthly_days: Number(event.target.value) })} /></label>
          <label style={styles.label}>Regular leave / month<input type="number" min="0.01" step="0.01" required value={policy.regular_monthly_days} style={styles.input} onChange={(event) => setPolicy({ ...policy, regular_monthly_days: Number(event.target.value) })} /></label>
          <label style={styles.label}>Paid leave type names<input value={policy.paid_leave_types.join(', ')} style={styles.input} onChange={(event) => setPolicy({ ...policy, paid_leave_types: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} /></label>
          <label style={styles.checkLabel}><input type="checkbox" checked={policy.allow_negative_balance} onChange={(event) => setPolicy({ ...policy, allow_negative_balance: event.target.checked })} /> Allow negative balances</label>
        </div>
        <button type="submit" className="primary-action" disabled={saving}>{saving ? 'Saving…' : 'Save policy'}</button>
      </form>}

      <section style={styles.kpiGrid}>
        <Kpi label="Total employees" value={report?.employees.length ?? 0} />
        <Kpi label="Employees with available leave" value={totals.available} />
        <Kpi label="Exhausted / overdrawn" value={totals.overdrawn} alert={totals.overdrawn > 0} />
        <Kpi label="Paid leave used · selected period" value={`${totals.taken.toFixed(2)} days`} />
        <Kpi label="Unpaid leave · selected period" value={`${totals.unpaid.toFixed(2)} days`} />
        <Kpi label="Pending requests" value={totals.pending} />
      </section>

      <section className="surface-card" style={styles.reportCard}>
        <div style={styles.sectionHeader}>
          <div><h3 style={styles.title}>Employee Paid Leave Balances</h3><p style={styles.muted}>Selected period: {report?.period ?? period} · Calculated on {report?.as_of ?? '…'}</p></div>
          {loading && <span style={styles.muted}>Refreshing…</span>}
        </div>
        <div className="paid-leave-filters" style={styles.filters}>
          <input aria-label="Search employee" placeholder="Search name, email or ID" value={search} style={styles.input} onChange={(event) => setSearch(event.target.value)} />
          <select aria-label="Period type" value={periodType} style={styles.input} onChange={(event) => changePeriodType(event.target.value as PaidLeaveReportFilters['periodType'])}>
            <option value="month">Month</option><option value="quarter">Quarter</option><option value="financial_year">Financial year</option>
          </select>
          {periodType === 'month' && <input aria-label="Month" type="month" value={period} style={styles.input} onChange={(event) => setPeriod(event.target.value)} />}
          {periodType === 'quarter' && <select aria-label="Quarter" value={period} style={styles.input} onChange={(event) => setPeriod(event.target.value)}>{Array.from({ length: 12 }, (_, index) => { const date = new Date(); date.setMonth(date.getMonth() - index * 3); return `${date.getFullYear()}-Q${Math.floor(date.getMonth() / 3) + 1}`; }).map((value) => <option key={value}>{value}</option>)}</select>}
          {periodType === 'financial_year' && <select aria-label="Financial year" value={period} style={styles.input} onChange={(event) => setPeriod(event.target.value)}>{Array.from({ length: 8 }, (_, index) => { const year = new Date().getFullYear() - (new Date().getMonth() < 3 ? 1 : 0) - index; return `${year}-${String(year + 1).slice(-2)}`; }).map((value) => <option key={value}>{value}</option>)}</select>}
          <select aria-label="Filter department" value={department} style={styles.input} onChange={(event) => setDepartment(event.target.value)}><option value="">All departments</option>{departments.map((value) => <option key={value}>{value}</option>)}</select>
          <select aria-label="Filter designation" value={designation} style={styles.input} onChange={(event) => setDesignation(event.target.value)}><option value="">All designations</option>{designations.map((value) => <option key={value}>{value}</option>)}</select>
          <select aria-label="Filter probation status" value={probationStatus} style={styles.input} onChange={(event) => setProbationStatus(event.target.value)}><option value="">All eligibility</option><option>Probation</option><option>Regular</option><option>Unknown - joining date required</option></select>
          <select aria-label="Filter employment status" value={employmentStatus} style={styles.input} onChange={(event) => setEmploymentStatus(event.target.value)}><option value="">All employment statuses</option><option>Active</option><option>Pending</option><option>On Leave</option><option>Inactive</option></select>
          <select aria-label="Sort employees" value={sortBy} style={styles.input} onChange={(event) => setSortBy(event.target.value as PaidLeaveReportFilters['sortBy'])}><option value="employee_name">Sort: name</option><option value="remaining_balance">Sort: remaining balance</option><option value="utilization">Sort: utilization</option><option value="leave_taken">Sort: leave taken</option></select>
        </div>
        <div className="employee-table-scroll">
          <table style={styles.table}>
            <colgroup><col style={{ width: 220 }} /><col style={{ width: 180 }} /><col style={{ width: 120 }} /><col style={{ width: 135 }} /><col span={7} style={{ width: 110 }} /><col style={{ width: 115 }} /><col style={{ width: 90 }} /><col style={{ width: 130 }} /></colgroup>
            <thead><tr style={styles.groupHeader}>
              <th colSpan={4}>Employee</th><th colSpan={7}>Paid leave balance</th><th>Unpaid leave</th><th>Requests</th><th>Utilization</th>
            </tr><tr style={styles.columnHeader}>
              <th style={styles.stickyHeader}>Employee</th><th>Department / designation</th><th>Joining date</th><th>Eligibility / status</th><th>Monthly allowance</th><th>Monthly credit</th><th>Opening balance</th><th>HR adjustments</th><th>Paid used</th><th>Remaining balance</th><th>Credited total*</th><th>Used in period</th><th>Pending</th><th>Usage</th>
            </tr></thead>
            <tbody>
              {report?.employees.map((row) => <tr key={row.employee_id} style={{ ...styles.row, ...(row.exhausted ? styles.exhaustedRow : {}), ...(selectedEmployeeId === row.employee_id ? styles.selectedRow : {}) }}>
                <td style={styles.stickyCell}><button type="button" className="employee-detail-link" style={styles.employeeName} onClick={() => setSelectedEmployeeId(row.employee_id)}>{row.employee_name}</button><small>#{row.employee_id} · {row.email}</small></td>
                <td style={styles.wrapCell}><strong>{row.department}</strong><small>{row.designation}</small></td>
                <td>{row.date_of_joining || '—'}</td>
                <td><span style={{ ...styles.badge, ...badge(row.employment_status) }}>{row.employment_status}</span><small>{row.employee_status}</small></td>
                <td>{row.monthly_entitlement.toFixed(2)} days</td>
                <td>{row.current_month_credit.toFixed(2)}</td>
                <td>{row.opening_balance.toFixed(2)}</td>
                <td>{row.manual_adjustments > 0 ? '+' : ''}{row.manual_adjustments.toFixed(2)}</td>
                <td>{row.period_taken.toFixed(2)}</td>
                <td><strong style={row.remaining_balance <= 0 ? styles.zeroBalance : styles.availableBalance}>{row.remaining_balance.toFixed(2)} days</strong>{row.overdrawn && <small style={styles.overdrawnLabel}>Overdrawn</small>}{row.remaining_balance === 0 && !row.overdrawn && <small style={styles.exhaustedLabel}>No balance</small>}</td>
                <td>{row.total_credited.toFixed(2)}</td>
                <td>{row.period_unpaid.toFixed(2)}</td>
                <td>{row.pending_requests}</td>
                <td><div style={styles.utilizationCell}><span>{row.utilization_percent.toFixed(1)}%</span><small>{row.never_taken ? 'Not taken' : row.utilization_percent >= 80 ? 'High usage' : row.utilization_percent < 25 ? 'Low usage' : 'In use'}</small><span style={styles.utilTrack}><i style={{ ...styles.utilBar, width: `${Math.min(Math.max(row.utilization_percent, 0), 100)}%` }} /></span></div></td>
              </tr>)}
              {!loading && report?.employees.length === 0 && <tr><td colSpan={14} style={styles.empty}>No employees match these filters.</td></tr>}
            </tbody>
          </table>
        </div>
        <small style={styles.muted}>*Credited includes signed HR adjustments. Remaining = credited − approved paid leave. Pending, rejected, and cancelled requests do not reduce the balance.</small>
      </section>

      {details && <section className="surface-card" style={styles.detailsCard}>
        <div style={styles.sectionHeader}><div><h3 style={styles.title}>{details.employee.name} · Paid leave detail</h3><p style={styles.muted}>{details.employee.department} · {details.employee.designation} · Joined {details.employee.date_of_joining || '—'} · Probation through {details.employee.probation_end_date || '—'} · Regular from {details.employee.regular_start_date || '—'}</p></div>
          <button type="button" className="secondary-action" onClick={() => setShowAdjustment((shown) => !shown)}>Adjust balance</button>
        </div>
        {showAdjustment && <form onSubmit={saveAdjustment} style={styles.adjustmentForm}>
          <label style={styles.label}>Adjustment days (+/-)<input type="number" step="0.01" required value={adjustment.amount} style={styles.input} onChange={(event) => setAdjustment({ ...adjustment, amount: Number(event.target.value) })} /></label>
          <label style={styles.label}>Effective date<input type="date" required value={adjustment.effective_date} style={styles.input} onChange={(event) => setAdjustment({ ...adjustment, effective_date: event.target.value })} /></label>
          <label style={styles.label}>Reason<input required minLength={3} value={adjustment.reason} style={styles.input} onChange={(event) => setAdjustment({ ...adjustment, reason: event.target.value })} /></label>
          <button type="submit" className="primary-action" disabled={saving}>Record audited adjustment</button>
        </form>}
        <div style={styles.detailGrid}>
          <div><h4 style={styles.subheading}>Month-wise balance</h4><table style={styles.detailTable}><thead><tr><th>Month</th><th>Opening / carry-forward</th><th>New credit</th><th>Paid used</th><th>Unpaid used</th><th>Adjustments</th><th>Closing</th></tr></thead><tbody>{details.monthly_history.map((item) => <tr key={item.month}><td>{item.month}</td><td>{item.opening_balance.toFixed(2)}</td><td>{item.credited.toFixed(2)}</td><td>{item.used.toFixed(2)}</td><td>{item.unpaid_used.toFixed(2)}</td><td>{item.adjustments.toFixed(2)}</td><td><strong>{item.closing_balance.toFixed(2)}</strong></td></tr>)}</tbody></table></div>
          <div><h4 style={styles.subheading}>Leave request history</h4><div style={styles.historyList}>{details.requests.map((request) => <article key={request.id} style={styles.historyItem}><strong>{request.type} · {request.days?.toFixed(2) ?? '0.00'} requested days · {request.start_date}{request.start_date !== request.end_date ? ` to ${request.end_date}` : ''}</strong><span>{request.status}</span><small>Paid: {(request.paid_days ?? 0).toFixed(2)} · Unpaid: {(request.unpaid_days ?? 0).toFixed(2)} · {request.reason}</small></article>)}</div></div>
        </div>
        <h4 style={styles.subheading}>Audit ledger</h4><div className="employee-table-scroll"><table style={styles.detailTable}><thead><tr><th>Date</th><th>Type</th><th>Amount</th><th>Period</th><th>Reason / source</th><th>Entered by</th></tr></thead><tbody>{details.ledger.map((entry) => <tr key={entry.id}><td>{entry.effective_date}</td><td>{entry.type}</td><td>{entry.amount > 0 ? '+' : ''}{entry.amount.toFixed(2)}</td><td>{entry.period || '—'}</td><td>{entry.note}</td><td>{entry.created_by}</td></tr>)}</tbody></table></div>
      </section>}
    </Layout>
  );
}

function Kpi({ label, value, alert = false }: { label: string; value: string | number; alert?: boolean }) {
  return <div className="surface-card" style={{ ...styles.kpi, ...(alert ? styles.kpiAlert : {}) }}><span>{label}</span><strong>{value}</strong></div>;
}

const styles: Record<string, React.CSSProperties> = {
  headerActions: { display: 'flex', gap: '8px', flexWrap: 'wrap' },
  notice: { padding: '12px', borderRadius: '10px', marginBottom: '14px' },
  success: { padding: '12px', borderRadius: '10px', marginBottom: '14px', background: '#e5f8ef', color: '#17623e' },
  policyPanel: { padding: '21px', borderRadius: '18px', marginBottom: '18px' },
  sectionHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '14px', flexWrap: 'wrap', marginBottom: '15px' },
  title: { margin: 0, color: '#172b46', fontSize: '1.1rem' },
  muted: { margin: '5px 0 0', color: '#61718a', fontSize: '.8rem' },
  policyGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(185px, 1fr))', gap: '12px', marginBottom: '15px' },
  label: { display: 'flex', flexDirection: 'column', gap: '6px', color: '#354963', fontSize: '.78rem', fontWeight: 700 },
  input: { minWidth: 0, padding: '10px 11px', color: '#152641', border: '1px solid #cbd7e6', borderRadius: '9px', background: '#fff' },
  checkLabel: { display: 'flex', alignItems: 'center', gap: '8px', color: '#354963', fontSize: '.82rem' },
  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '18px' },
  kpi: { padding: '16px', borderRadius: '14px', display: 'flex', flexDirection: 'column', gap: '8px', color: '#526681', fontSize: '.75rem', fontWeight: 700 },
  kpiAlert: { borderColor: '#f4b4b4', background: '#fff2f2', color: '#9a2929' },
  kpiAlertValue: { color: '#9a2929' },
  reportCard: { padding: '21px', borderRadius: '18px', marginBottom: '18px' },
  filters: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '9px', marginBottom: '15px' },
  table: { width: '100%', minWidth: '1480px', borderCollapse: 'separate', borderSpacing: 0, fontSize: '.8rem', color: '#263a56' },
  groupHeader: { background: '#edf3fa', color: '#526681', fontSize: '.72rem', textTransform: 'uppercase', letterSpacing: '.04em' },
  columnHeader: { background: '#f8fafc', color: '#334b68', fontSize: '.74rem' },
  row: { borderBottom: '1px solid #e8edf4', height: '68px' },
  stickyHeader: { position: 'sticky', left: 0, zIndex: 3, background: '#f8fafc' },
  stickyCell: { position: 'sticky', left: 0, zIndex: 2, background: '#fff', boxShadow: '5px 0 8px -8px rgba(15, 23, 42, .45)' },
  employeeName: { display: 'block', maxWidth: '205px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 800, textAlign: 'left' },
  wrapCell: { whiteSpace: 'normal', maxWidth: '180px' },
  availableBalance: { color: '#176b60' },
  exhaustedRow: { background: '#fff4f3' },
  selectedRow: { outline: '2px solid #6d66e8', outlineOffset: '-2px' },
  badge: { display: 'inline-flex', padding: '5px 8px', borderRadius: '999px', fontSize: '.7rem', fontWeight: 800 },
  zeroBalance: { color: '#a33434' },
  exhaustedLabel: { display: 'block', color: '#b42318', fontSize: '.61rem', letterSpacing: '.04em' },
  overdrawnLabel: { display: 'block', color: '#842029', fontSize: '.61rem', fontWeight: 900 },
  utilizationCell: { display: 'flex', flexDirection: 'column', gap: '5px' },
  utilTrack: { display: 'block', width: '76px', height: '5px', background: '#e5eaf2', borderRadius: '999px', overflow: 'hidden' },
  utilBar: { display: 'block', height: '100%', background: 'linear-gradient(90deg, #07b7a3, #6257e8)', borderRadius: '999px' },
  empty: { padding: '24px', textAlign: 'center', color: '#61718a' },
  detailsCard: { padding: '21px', borderRadius: '18px', marginBottom: '24px' },
  adjustmentForm: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px', padding: '14px', marginBottom: '18px', borderRadius: '12px', background: '#f6f8fc' },
  detailGrid: { display: 'grid', gridTemplateColumns: 'minmax(0, 1.15fr) minmax(250px, .85fr)', gap: '18px', margin: '18px 0' },
  subheading: { margin: '0 0 10px', color: '#243957', fontSize: '.92rem' },
  detailTable: { width: '100%', borderCollapse: 'collapse', fontSize: '.76rem', textAlign: 'left' },
  historyList: { display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '310px', overflow: 'auto' },
  historyItem: { display: 'grid', gridTemplateColumns: '1fr auto', gap: '4px 10px', padding: '10px', border: '1px solid #e2e9f2', borderRadius: '10px', color: '#263a56', fontSize: '.77rem' },
  historySmall: { color: '#61718a' },
};
