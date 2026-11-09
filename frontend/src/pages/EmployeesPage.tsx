import { useState, type FormEvent } from 'react';
import { Layout } from '../components/Layout';
import { getEmployeeOnboarding, type EmployeeUpdate } from '../services/api';
import type { Employee } from '../types';

type EmployeesPageProps = {
  employees: Employee[];
  onRegister: (payload: {
    name: string;
    email: string;
    role: string;
    department: string;
    location: string;
    status: Employee['status'];
    manager: string;
    password: string;
    phone?: string;
    start_date: string;
    employment_type: string;
    emergency_contact_name?: string;
    emergency_contact_relationship?: string;
    emergency_contact_phone?: string;
  }) => Promise<void>;
  onUpdate: (employeeId: number, payload: EmployeeUpdate) => Promise<void>;
  onArchive: (employee: Employee) => Promise<void>;
  onOpenProfile: (employee: Employee) => void;
};

export function EmployeesPage({ employees, onRegister, onUpdate, onArchive, onOpenProfile }: EmployeesPageProps) {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEmployeeId, setEditingEmployeeId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [form, setForm] = useState({
    name: '',
    email: '',
    role: '',
    department: '',
    location: '',
    status: 'Active' as Employee['status'],
    manager: '',
    password: '',
    phone: '',
    start_date: new Date().toISOString().slice(0, 10),
    employment_type: 'Full-time',
    emergency_contact_name: '',
    emergency_contact_relationship: '',
    emergency_contact_phone: '',
  });

  const submitRegistration = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      if (editingEmployeeId === null) {
        await onRegister(form);
      } else {
        const { password: _password, ...updates } = form;
        await onUpdate(editingEmployeeId, updates);
      }
      setForm({ name: '', email: '', role: '', department: '', location: '', status: 'Pending', manager: '', password: '', phone: '', start_date: new Date().toISOString().slice(0, 10), employment_type: 'Full-time', emergency_contact_name: '', emergency_contact_relationship: '', emergency_contact_phone: '' });
      setEditingEmployeeId(null);
      setIsFormOpen(false);
    } catch (registrationError) {
      setError(registrationError instanceof Error ? registrationError.message : 'Could not register employee.');
    } finally {
      setSaving(false);
    }
  };

  const openEditForm = async (employee: Employee) => {
    setSaving(true);
    setError('');
    setActionError('');
    try {
      const profile = await getEmployeeOnboarding(employee.id).catch(() => null);
      setForm({
        name: employee.name,
        email: employee.email,
        role: employee.role,
        department: employee.department,
        location: employee.location,
        status: employee.status,
        manager: employee.manager,
        password: '',
        phone: profile?.phone || employee.phone || '',
        start_date: profile?.start_date || employee.start_date || new Date().toISOString().slice(0, 10),
        employment_type: profile?.employment_type || 'Full-time',
        emergency_contact_name: profile?.emergency_contact_name || '',
        emergency_contact_relationship: profile?.emergency_contact_relationship || '',
        emergency_contact_phone: profile?.emergency_contact_phone || '',
      });
      setEditingEmployeeId(employee.id);
      setIsFormOpen(true);
    } catch (loadError) {
      setActionError(loadError instanceof Error ? loadError.message : 'Unable to load employee details.');
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async (employee: Employee) => {
    if (!window.confirm(`Archive ${employee.name}? Their sign-in will be disabled, while leave, attendance and onboarding history will be retained.`)) return;
    setActionError('');
    try {
      await onArchive(employee);
    } catch (archiveError) {
      setActionError(archiveError instanceof Error ? archiveError.message : 'Unable to archive employee.');
    }
  };

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const visibleEmployees = normalizedSearch
    ? employees.filter((employee) =>
      employee.name.toLowerCase().includes(normalizedSearch)
      || String(employee.id).includes(normalizedSearch)
    )
    : employees;

  return (
    <Layout
      title="Employees"
      subtitle="People management"
      actions={<button type="button" className="primary-action" style={styles.primaryButton} onClick={() => { setError(''); setEditingEmployeeId(null); setForm({ name: '', email: '', role: '', department: '', location: '', status: 'Pending', manager: '', password: '', phone: '', start_date: new Date().toISOString().slice(0, 10), employment_type: 'Full-time', emergency_contact_name: '', emergency_contact_relationship: '', emergency_contact_phone: '' }); setIsFormOpen(true); }}>Add employee</button>}
    >
      {actionError && <div role="alert" className="error-banner" style={styles.error}>{actionError}</div>}
      {isFormOpen && (
        <div style={styles.overlay} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setIsFormOpen(false); }}>
          <form className="employee-modal" style={styles.modal} onSubmit={submitRegistration}>
            <div style={styles.modalHeader}>
              <div>
                <h2 style={styles.modalTitle}>{editingEmployeeId === null ? 'Register employee' : 'Edit employee details'}</h2>
                <p style={styles.modalSubtitle}>{editingEmployeeId === null ? 'Create the employee record, portal account, profile and onboarding checklist.' : 'Update employee and emergency contact information.'}</p>
              </div>
              <button type="button" onClick={() => setIsFormOpen(false)} style={styles.closeButton} aria-label="Close">×</button>
            </div>
            {error && <div role="alert" className="error-banner" style={styles.error}>{error}</div>}
            <div style={styles.formGrid}>
              <label style={styles.field}>Full name<input required autoComplete="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={styles.input} /></label>
              <label style={styles.field}>Work email<input required type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} style={styles.input} /></label>
              <label style={styles.field}>Job title<input required value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} style={styles.input} /></label>
              <label style={styles.field}>Department<input required value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} style={styles.input} /></label>
              <label style={styles.field}>Location<input required value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} style={styles.input} /></label>
              <label style={styles.field}>Manager<input required value={form.manager} onChange={(e) => setForm({ ...form, manager: e.target.value })} style={styles.input} /></label>
              <label style={styles.field}>Phone<input type="tel" autoComplete="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} style={styles.input} /></label>
              <label style={styles.field}>Start date<input required type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} style={styles.input} /></label>
              <label style={styles.field}>Employment type<select value={form.employment_type} onChange={(e) => setForm({ ...form, employment_type: e.target.value })} style={styles.input}><option>Full-time</option><option>Part-time</option><option>Contract</option><option>Intern</option></select></label>
              <label style={styles.field}>Emergency contact name<input value={form.emergency_contact_name} onChange={(e) => setForm({ ...form, emergency_contact_name: e.target.value })} style={styles.input} /></label>
              <label style={styles.field}>Emergency contact relationship<input value={form.emergency_contact_relationship} onChange={(e) => setForm({ ...form, emergency_contact_relationship: e.target.value })} style={styles.input} /></label>
              <label style={styles.field}>Emergency contact phone<input type="tel" value={form.emergency_contact_phone} onChange={(e) => setForm({ ...form, emergency_contact_phone: e.target.value })} style={styles.input} /></label>
              {editingEmployeeId === null && <label style={styles.field}>Temporary password<input required type="password" minLength={12} autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} style={styles.input} /><small style={styles.help}>At least 12 characters</small></label>}
              <p style={styles.privacyNote}>Do not enter Aadhaar, PAN, bank details or identity document numbers here. Store highly sensitive records only through approved restricted-access systems.</p>
            </div>
            <div style={styles.modalActions}>
              <button type="button" style={styles.cancelButton} onClick={() => setIsFormOpen(false)}>Cancel</button>
              <button type="submit" className="primary-action" style={styles.primaryButton} disabled={saving}>{saving ? 'Saving…' : editingEmployeeId === null ? 'Register employee' : 'Save changes'}</button>
            </div>
          </form>
        </div>
      )}
      <div style={styles.searchBar}>
        <label htmlFor="employee-search" style={styles.searchLabel}>Search employees</label>
        <input
          id="employee-search"
          type="search"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="Search by employee name or ID"
          style={styles.searchInput}
        />
        <button type="button" className="secondary-action" style={styles.searchButton} onClick={() => setSearchTerm(searchTerm.trim())}>Search</button>
        {searchTerm && <button type="button" style={styles.clearButton} onClick={() => setSearchTerm('')}>Clear</button>}
      </div>
      {normalizedSearch && <p style={styles.searchResult}>
        {visibleEmployees.length ? `${visibleEmployees.length} employee${visibleEmployees.length === 1 ? '' : 's'} found.` : 'No employee matched that name or ID.'}
      </p>}
      <div className="data-table-wrap">
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Name</th>
              <th style={styles.th}>Work email</th>
              <th style={styles.th}>Role</th>
              <th style={styles.th}>Department</th>
              <th style={styles.th}>Start date</th>
              <th style={styles.th}>Location</th>
              <th style={styles.th}>Status</th>
              <th style={styles.th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleEmployees.map((employee) => (
              <tr key={employee.id}>
                <td style={styles.td}>{employee.name}</td>
                <td style={styles.td}>{employee.email}</td>
                <td style={styles.td}>{employee.role}</td>
                <td style={styles.td}>{employee.department}</td>
                <td style={styles.td}>{employee.start_date || '—'}</td>
                <td style={styles.td}>{employee.location}</td>
                <td style={styles.td}>
                  <span style={{ ...styles.statusPill, ...statusColors[employee.status] }}>
                    {employee.status}
                  </span>
                </td>
                <td style={styles.td}>
                  <div style={styles.rowActions}>
                    <button type="button" className="secondary-action" style={styles.smallButton} disabled={saving} onClick={() => openEditForm(employee)}>Edit</button>
                    <button type="button" className="secondary-action" style={styles.smallButton} onClick={() => onOpenProfile(employee)}>360° profile</button>
                    {employee.status !== 'Inactive' && <button type="button" style={styles.archiveButton} onClick={() => handleArchive(employee)}>Archive</button>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}

const statusColors: Record<string, React.CSSProperties> = {
  Active: { background: '#dcfce7', color: '#166534' },
  'On Leave': { background: '#fef3c7', color: '#92400e' },
  Pending: { background: '#e0e7ff', color: '#3730a3' },
  Inactive: { background: '#e2e8f0', color: '#334155' },
};

const styles: Record<string, React.CSSProperties> = {
  tableWrap: {
    background: '#fff',
    borderRadius: '18px',
    border: '1px solid #e2e8f0',
    overflow: 'hidden',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    textAlign: 'left',
    padding: '16px 18px',
    background: '#f8fafc',
    color: '#475569',
    fontSize: '0.8rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  td: {
    padding: '16px 18px',
    borderTop: '1px solid #e2e8f0',
    color: '#1e293b',
  },
  statusPill: {
    display: 'inline-block',
    padding: '6px 10px',
    borderRadius: '999px',
    fontSize: '0.75rem',
    fontWeight: 700,
  },
  primaryButton: {
    background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
    color: '#fff',
    border: 'none',
    borderRadius: '12px',
    padding: '12px 16px',
    fontWeight: 700,
    cursor: 'pointer',
  },
  overlay: {
    position: 'fixed',
    inset: 0,
    zIndex: 20,
    display: 'grid',
    placeItems: 'center',
    padding: '20px',
    background: 'rgba(15, 23, 42, 0.55)',
  },
  modal: {
    width: 'min(720px, 100%)',
    maxHeight: 'calc(100vh - 40px)',
    overflowY: 'auto',
    background: '#fff',
    borderRadius: '20px',
    padding: '26px',
    boxShadow: '0 24px 80px rgba(15, 23, 42, 0.25)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '20px',
  },
  modalTitle: { margin: 0, fontSize: '1.4rem' },
  modalSubtitle: { margin: '6px 0 0', color: '#64748b', fontSize: '0.9rem' },
  closeButton: { border: 0, background: 'transparent', fontSize: '1.7rem', cursor: 'pointer', color: '#64748b' },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '16px' },
  field: { display: 'flex', flexDirection: 'column', gap: '7px', color: '#475569', fontSize: '0.85rem', fontWeight: 600 },
  input: { width: '100%', boxSizing: 'border-box', border: '1px solid #dbe2f0', borderRadius: '10px', padding: '11px 12px', fontSize: '0.95rem', background: '#f8fafc', color: '#0f172a' },
  help: { color: '#64748b', fontWeight: 400 },
  error: { marginBottom: '16px', padding: '11px 13px', borderRadius: '10px', background: '#fee2e2', color: '#991b1b' },
  modalActions: { display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' },
  cancelButton: { border: '1px solid #cbd5e1', borderRadius: '12px', padding: '12px 16px', background: '#fff', color: '#334155', fontWeight: 700, cursor: 'pointer' },
  rowActions: { display: 'flex', gap: '8px', alignItems: 'center' },
  smallButton: { padding: '7px 10px', fontSize: '.8rem' },
  archiveButton: { border: '1px solid #fecaca', borderRadius: '9px', padding: '7px 10px', color: '#991b1b', background: '#fff1f2', fontWeight: 700, cursor: 'pointer', fontSize: '.8rem' },
  searchBar: { display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '8px', padding: '14px 16px', background: '#fff', border: '1px solid #e2e8f0', borderRadius: '14px' },
  searchLabel: { fontWeight: 700, color: '#334155', fontSize: '0.85rem' },
  searchInput: { flex: '1 1 280px', minWidth: '220px', border: '1px solid #cbd5e1', borderRadius: '10px', padding: '10px 12px', fontSize: '0.95rem', color: '#0f172a' },
  searchButton: { padding: '10px 15px' },
  clearButton: { border: '1px solid #cbd5e1', borderRadius: '9px', padding: '9px 13px', background: '#fff', color: '#334155', fontWeight: 700, cursor: 'pointer' },
  searchResult: { margin: '0 0 12px', color: '#64748b', fontSize: '0.85rem' },
};
