import { useCallback, useEffect, useState } from 'react';
import { ForgotPasswordScreen, LoginScreen } from './components/AuthScreens';
import { AttendancePage } from './pages/AttendancePage';
import { DashboardPage } from './pages/DashboardPage';
import { EmployeesPage } from './pages/EmployeesPage';
import { EmployeeLifecyclePage } from './pages/EmployeeLifecyclePage';
import { Employee360Page } from './pages/Employee360Page';
import { EmployeeSelfServicePage } from './pages/EmployeeSelfServicePage';
import { EmployeeOnboardingPage } from './pages/EmployeeOnboardingPage';
import { ProgressReportsPage } from './pages/ProgressReportsPage';
import { LeavePage } from './pages/LeavePage';
import { OnboardingPage } from './pages/OnboardingPage';
import { PaidLeavePage } from './pages/PaidLeavePage';
import { NotificationCenter } from './components/NotificationCenter';
import { archiveEmployee, getDashboardData, getEmployees, loginApi, registerEmployee, updateEmployee, type EmployeeUpdate } from './services/api';
import type { DashboardData, Employee, User } from './types';

export default function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    try {
      return JSON.parse(localStorage.getItem('hr_user') || 'null') as User | null;
    } catch {
      return null;
    }
  });
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(localStorage.getItem('hr_token') && localStorage.getItem('hr_user')));
  const [screen, setScreen] = useState<'login' | 'reset'>('login');
  const [page, setPage] = useState<'dashboard' | 'my-360' | 'my-onboarding' | 'progress-reports' | 'employees' | 'employee-360' | 'onboarding' | 'lifecycle' | 'paid-leave' | 'leave' | 'attendance' | 'recruiting'>('dashboard');
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionError, setSessionError] = useState('');
  const [notificationCounts, setNotificationCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!isAuthenticated) return;

    const load = async () => {
      setLoading(true);
      try {
        const [dashboard, employeeList] = await Promise.all([
          getDashboardData(),
          currentUser?.role === 'HR Manager' ? getEmployees() : Promise.resolve({ employees: [] as Employee[] }),
        ]);
        setDashboardData(dashboard);
        setEmployees(employeeList.employees);
      } catch (error) {
        setSessionError(error instanceof Error ? `Signed in, but the portal could not load: ${error.message}` : 'Signed in, but the portal could not load. Check that the backend and database are available.');
        localStorage.removeItem('hr_token');
        localStorage.removeItem('hr_user');
        setCurrentUser(null);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [isAuthenticated, currentUser]);

  const handleLoginSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const email = (form.querySelector('input[type="email"]') as HTMLInputElement)?.value || '';
    const password = (form.querySelector('input[type="password"]') as HTMLInputElement)?.value || '';

    setLoading(true);
    try {
      const response = await loginApi(email, password);
      setSessionError('');
      localStorage.setItem('hr_token', response.token);
      localStorage.setItem('hr_user', JSON.stringify(response.user));
      setCurrentUser(response.user);
      setIsAuthenticated(true);
      setPage('dashboard');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterEmployee = async (payload: Parameters<typeof registerEmployee>[0]) => {
    await registerEmployee(payload);
    const [employeeList, dashboard] = await Promise.all([getEmployees(), getDashboardData()]);
    setEmployees(employeeList.employees);
    setDashboardData(dashboard);
  };

  const refreshEmployees = async () => {
    const [employeeList, dashboard] = await Promise.all([getEmployees(), getDashboardData()]);
    setEmployees(employeeList.employees);
    setDashboardData(dashboard);
  };

  const refreshDashboard = async () => {
    setDashboardData(await getDashboardData());
  };

  const handleUpdateEmployee = async (employeeId: number, payload: EmployeeUpdate) => {
    await updateEmployee(employeeId, payload);
    await refreshEmployees();
  };

  const handleArchiveEmployee = async (employee: Employee) => {
    await archiveEmployee(employee.id);
    await refreshEmployees();
  };

  const handleLogout = () => {
    localStorage.removeItem('hr_token');
    localStorage.removeItem('hr_user');
    setCurrentUser(null);
    setIsAuthenticated(false);
    setDashboardData(null);
    setEmployees([]);
    setPage('dashboard');
    setNotificationCounts({});
  };

  const navigateFromNotification = useCallback((module: string, link: string | null) => {
    const target = link || '';
    if (target.includes('progress') || module === 'tasks') setPage(currentUser?.role === 'HR Manager' ? 'progress-reports' : 'my-360');
    else if (module === 'onboarding') setPage(currentUser?.role === 'HR Manager' ? 'onboarding' : 'my-onboarding');
    else if (module === 'employees') setPage('employees');
    else if (module === 'attendance') setPage('attendance');
    else setPage('leave');
  }, [currentUser?.role]);

  if (!isAuthenticated && screen === 'login') {
    return (
      <LoginScreen
        onForgotPassword={() => setScreen('reset')}
        onSubmit={handleLoginSubmit}
        error={sessionError}
      />
    );
  }

  if (!isAuthenticated && screen === 'reset') {
    return (
      <ForgotPasswordScreen
        onBackToLogin={() => setScreen('login')}
      />
    );
  }

  if (loading || !dashboardData) {
    return <div className="loading-screen">Loading HR portal...</div>;
  }

  return (
    <div className="app-shell">
        <aside className="app-sidebar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '30px' }}>
            <div className="brand-mark" style={{ width: '42px', height: '42px', borderRadius: '12px', background: 'linear-gradient(135deg, #19c7ad, #6a61f6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>H</div>
            <div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>HR Portal</div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>People Ops</div>
            </div>
          </div>

          <nav style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[
              { key: 'dashboard', label: 'Dashboard', icon: '⌂' },
              ...(currentUser?.role !== 'HR Manager' ? [{ key: 'my-360', label: 'My Employee Dashboard', icon: '◎' }] : []),
              ...(currentUser?.role !== 'HR Manager' ? [{ key: 'my-onboarding', label: 'My Onboarding', icon: '✦' }] : []),
              { key: 'leave', label: 'Leave', icon: '◫' },
              { key: 'attendance', label: 'Attendance', icon: '◷' },
              ...(currentUser?.role === 'HR Manager' ? [
                { key: 'employees', label: 'Employees', icon: '◌' },
                { key: 'onboarding', label: 'Onboarding', icon: '✦' },
                { key: 'lifecycle', label: 'Lifecycle', icon: '↗' },
                { key: 'paid-leave', label: 'Paid Leave', icon: '◇' },
                { key: 'progress-reports', label: 'Progress Reports', icon: '▤' },
              ] : []),
              { key: 'recruiting', label: 'Recruiting', icon: '✧' },
            ].map((item) => (
              <button
                key={item.key}
                onClick={() => setPage(item.key as 'dashboard' | 'my-360' | 'my-onboarding' | 'progress-reports' | 'employees' | 'employee-360' | 'onboarding' | 'lifecycle' | 'paid-leave' | 'leave' | 'attendance' | 'recruiting')}
                className={`nav-item ${page === item.key ? 'nav-item-active' : ''}`}
                aria-current={page === item.key ? 'page' : undefined}
                style={{
                  border: 'none',
                  borderRadius: '12px',
                  padding: '12px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  width: '100%',
                  minWidth: 0,
                  background: page === item.key ? 'rgba(99, 102, 241, 0.18)' : 'transparent',
                  color: page === item.key ? '#fff' : '#e2e8f0',
                  opacity: 1,
                  visibility: 'visible',
                  cursor: 'pointer',
                  fontWeight: 700,
                }}
              >
                <span className="nav-icon" aria-hidden="true">{item.icon}</span>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.label}</span>
                {((notificationCounts[item.key] || 0) > 0 || (item.key === 'progress-reports' && (notificationCounts.tasks || 0) > 0)) && <span style={styles.moduleDot} aria-label="Unread notifications" />}
              </button>
            ))}
          </nav>
          <div className="sidebar-profile">
            <div className="avatar-badge" aria-hidden="true">{currentUser?.name.charAt(0).toUpperCase() || 'U'}</div>
            <div className="sidebar-profile-copy">
              <strong>{currentUser?.name}</strong>
              <span>{currentUser?.role}</span>
            </div>
            <button type="button" className="logout-button" onClick={handleLogout}>Log out</button>
          </div>
        </aside>

        <main className="app-main">
          <div className="main-toolbar"><NotificationCenter onNavigate={navigateFromNotification} onCountsChange={setNotificationCounts} /></div>
          {page === 'dashboard' && <DashboardPage data={dashboardData} />}
          {page === 'my-360' && currentUser?.role !== 'HR Manager' && <EmployeeSelfServicePage />}
          {page === 'my-onboarding' && currentUser?.role !== 'HR Manager' && <EmployeeOnboardingPage />}
          {page === 'progress-reports' && currentUser?.role === 'HR Manager' && <ProgressReportsPage />}
          {page === 'employees' && currentUser?.role === 'HR Manager' && <EmployeesPage employees={employees} onRegister={handleRegisterEmployee} onUpdate={handleUpdateEmployee} onArchive={handleArchiveEmployee} onOpenProfile={(employee) => { setSelectedEmployee(employee); setPage('employee-360'); }} />}
          {page === 'employee-360' && currentUser?.role === 'HR Manager' && selectedEmployee && <Employee360Page employee={selectedEmployee} onBack={() => setPage('employees')} />}
          {page === 'onboarding' && <OnboardingPage employees={employees} onEmployeeActivated={refreshEmployees} />}
          {page === 'lifecycle' && currentUser?.role === 'HR Manager' && <EmployeeLifecyclePage employees={employees.filter((employee) => employee.status !== 'Inactive')} onRefresh={refreshEmployees} />}
          {page === 'paid-leave' && currentUser?.role === 'HR Manager' && <PaidLeavePage onChanged={refreshDashboard} />}
          {page === 'leave' && currentUser && <LeavePage user={currentUser} onBalanceChanged={refreshDashboard} />}
          {page === 'attendance' && currentUser && <AttendancePage user={currentUser} />}
          {page === 'recruiting' && (
            <div style={{ background: '#fff', borderRadius: '18px', padding: '28px', border: '1px solid #e2e8f0' }}>
              <h2>Recruiting</h2>
              <p>Candidate pipeline management is ready for the next module.</p>
            </div>
          )}
        </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  mainToolbar: { display: 'flex', justifyContent: 'flex-end', minHeight: 42, marginBottom: 8 },
  moduleDot: { display: 'inline-block', width: 7, height: 7, marginLeft: 8, verticalAlign: 'middle', borderRadius: '50%', background: '#f87171' },
};
