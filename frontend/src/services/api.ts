import type {
  AttendanceResponse,
  DashboardData,
  Employee,
  EmployeesResponse,
  LeaveRequest,
  LeaveRequestsResponse,
  LoginResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function todayInIndia(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date());
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('hr_token');
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
  } catch (error) {
    throw new Error(`Cannot reach HR API at ${API_BASE_URL}. Check that the backend is running and that its CORS origins include this frontend. ${error instanceof Error ? error.message : ''}`.trim());
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(errorBody?.detail || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function downloadReport(reportType: 'lifecycle' | 'employees' | 'attendance' | 'paid-leave' | 'leave' | 'employee-360', fileFormat: 'csv' | 'xlsx' | 'pdf', filters: Record<string, string | number | undefined> = {}): Promise<void> {
  const token = localStorage.getItem('hr_token');
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && String(value).length) query.set(key, String(value));
  }
  const suffix = query.size ? `?${query.toString()}` : '';
  const url = `${API_BASE_URL}/reports/${reportType}/${fileFormat}${suffix}`;
  let response: Response;
  try {
    response = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  } catch (error) {
    throw new Error(`Cannot reach report service at ${API_BASE_URL}. Check backend availability and CORS configuration. ${error instanceof Error ? error.message : ''}`.trim());
  }
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(errorBody?.detail || `Report download failed (${response.status})`);
  }
  const blob = await response.blob();
  if (!blob.size) throw new Error('The report service returned an empty file.');
  const disposition = response.headers.get('Content-Disposition') || '';
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || `${reportType}-report.${fileFormat}`;
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export async function loginApi(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function getDashboardData(): Promise<DashboardData> {
  return request<DashboardData>('/dashboard');
}

export type NotificationItem = {
  id: number;
  notification_type: string;
  title: string;
  message: string;
  module: string;
  related_record_id: number | null;
  action_link: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
};

export async function getNotifications(unreadOnly = false): Promise<{ notifications: NotificationItem[] }> {
  return request(`/notifications?limit=50${unreadOnly ? '&unread_only=true' : ''}`);
}

export async function getNotificationUnreadCount(): Promise<{ count: number }> {
  return request('/notifications/unread-count');
}

export async function getNotificationModuleCounts(): Promise<{ counts: Record<string, number> }> {
  return request('/notifications/module-counts');
}

export async function markNotificationRead(notificationId: number): Promise<void> {
  await request(`/notifications/${notificationId}/read`, { method: 'PATCH' });
}

export async function markAllNotificationsRead(): Promise<void> {
  await request('/notifications/read-all', { method: 'PATCH' });
}

export async function getEmployees(): Promise<EmployeesResponse> {
  return request<EmployeesResponse>('/employees');
}

export type Employee360Data = {
  employee: Pick<Employee, 'id' | 'name' | 'email' | 'role' | 'department' | 'manager' | 'status'>;
  activities: Array<{ id: number; activity_type: string; title: string; description: string | null; activity_date: string; actor_email: string }>;
  tasks: Array<{ id: number; title: string; description: string | null; priority: string; status: string; due_date: string | null; assigned_by: string; progress_percentage: number; progress_notes: string | null; overdue?: boolean }>;
  kras: Array<{ id: number; title: string; description: string | null; weight: number; period_start: string; period_end: string; status: string; progress_percentage: number; progress_notes: string | null; kpis: Array<{ id: number; name: string; target_value: number; actual_value: number | null; score: number | null; unit: string | null; status: string }> }>;
  reviews: Array<{ id: number; review_period: string; review_type: string; overall_score: number | null; strengths: string | null; development_areas: string | null; comments: string | null; status: string }>;
  progress_reports?: Array<{ id: number; period_type: string; period_start: string; period_end: string; summary: string; achievements: string | null; blockers: string | null; status: string; review_feedback: string | null }>;
  attendance?: { records_count: number; present: number; late: number; absent: number; attendance_rate: number };
  leave?: { request_count: number; status_counts: Record<string, number>; approved_days: number };
  goals?: Array<{ id: number; title: string; description: string | null; status: string; progress_percentage: number; target_date: string | null }>;
  development_plans?: Array<{ id: number; title: string; description: string | null; actions: string | null; status: string; target_date: string | null }>;
  documents?: Array<{ id: number; document_type: string; title: string; issuer: string | null; expiry_date: string | null; status: string }>;
  summary: { kra_count: number; kpi_count: number; average_kpi_score: number | null; average_review_score: number | null; open_tasks: number; completed_tasks: number; overdue_tasks?: number; task_completion_percentage?: number; task_status_counts?: Record<string, number> };
};

export async function getEmployee360(employeeId: number): Promise<Employee360Data> {
  return request<Employee360Data>(`/employees/${employeeId}/360`);
}

export async function getMyEmployee360(): Promise<Employee360Data> {
  return request<Employee360Data>('/me/360');
}

export async function addEmployeeActivity(employeeId: number, payload: { title: string; description?: string; activity_type?: string; activity_date?: string }): Promise<void> {
  await request(`/employees/${employeeId}/activities`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function addEmployeeTask(employeeId: number, payload: { title: string; description?: string; priority: string; due_date?: string }): Promise<void> {
  await request(`/employees/${employeeId}/tasks`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function addEmployeeKra(employeeId: number, payload: { title: string; description?: string; weight: number; period_start: string; period_end: string }): Promise<void> {
  await request(`/employees/${employeeId}/kras`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function addEmployeeReview(employeeId: number, payload: { review_period: string; overall_score?: number; comments?: string; strengths?: string; development_areas?: string }): Promise<void> {
  await request(`/employees/${employeeId}/reviews`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateEmployeeTask(taskId: number, payload: { status?: string; progress_percentage?: number; progress_notes?: string }): Promise<void> {
  await request(`/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export async function updateEmployeeKraProgress(kraId: number, payload: { progress_percentage: number; progress_notes?: string; status?: string }): Promise<void> {
  await request(`/kras/${kraId}/progress`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export async function updateMyKpiActual(kpiId: number, payload: { actual_value: number; notes?: string }): Promise<void> {
  await request(`/me/kpis/${kpiId}/actual`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export type ProgressReport = { id: number; period_type: string; period_start: string; period_end: string; summary: string; achievements: string | null; blockers: string | null; status: string; review_feedback: string | null };

export async function getMyProgressReports(): Promise<{ reports: ProgressReport[] }> {
  return request('/me/progress-reports');
}

export async function createMyProgressReport(payload: { period_type: string; period_start: string; period_end: string; summary: string; achievements?: string; blockers?: string }): Promise<ProgressReport> {
  return request('/me/progress-reports', { method: 'POST', body: JSON.stringify(payload) });
}

export async function submitMyProgressReport(reportId: number): Promise<ProgressReport> {
  return request(`/me/progress-reports/${reportId}/submit`, { method: 'POST' });
}

export async function getEmployeeProgressReports(employeeId: number): Promise<{ reports: ProgressReport[] }> {
  return request(`/employees/${employeeId}/progress-reports`);
}

export async function downloadEmployee360Summary(employeeId: number, employeeName: string): Promise<void> {
  const summary = await request<Record<string, unknown>>(`/employees/${employeeId}/360/summary`);
  const blob = new Blob([JSON.stringify(summary, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${employeeName.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}-360-summary.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function getAllProgressReports(): Promise<{ reports: Array<ProgressReport & { employee_id: number }> }> {
  return request('/reports/progress');
}

export async function reviewProgressReport(reportId: number, status: 'Under Review' | 'Reviewed', review_feedback: string): Promise<ProgressReport> {
  return request(`/progress-reports/${reportId}/review`, { method: 'PATCH', body: JSON.stringify({ status, review_feedback }) });
}

export type EmployeeRegistration = {
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
};

export async function registerEmployee(payload: EmployeeRegistration): Promise<Employee> {
  return request<Employee>('/employees', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export type EmployeeUpdate = Partial<Omit<EmployeeRegistration, 'password'>>;

export async function updateEmployee(employeeId: number, payload: EmployeeUpdate): Promise<Employee> {
  return request<Employee>(`/employees/${employeeId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function archiveEmployee(employeeId: number): Promise<{ message: string; id: number }> {
  return request<{ message: string; id: number }>(`/employees/${employeeId}`, {
    method: 'DELETE',
  });
}

export type ClearanceItem = {
  id: number;
  title: string;
  owner: string;
  status: 'Pending' | 'Completed';
  completed_by: string | null;
  completed_at: string | null;
};

export type LifecycleCase = {
  id: number;
  employee_id: number;
  case_type: 'Transfer' | 'Promotion' | 'Resignation' | 'Probation';
  status: string;
  effective_date: string;
  reason: string;
  changes: Record<string, string | number | boolean | null>;
  created_by: string;
  created_at: string;
  decided_at: string | null;
  clearance: ClearanceItem[];
};

export type EmployeeLifecycle = {
  employee_id: number;
  employee_name: string;
  department: string;
  location: string;
  role: string;
  manager: string;
  start_date: string | null;
  probation_due_date: string | null;
  probation_status: string;
  cases: LifecycleCase[];
  status_history: EmployeeStatusEvent[];
};

export type EmployeeStatusEvent = {
  id: number;
  previous_status: string;
  new_status: string;
  effective_date: string;
  reason: string;
  changed_by: string;
  created_at: string;
};

export type EmployeeLifecycleStatus = 'Active' | 'On Notice' | 'On Leave' | 'Pending' | 'Terminated' | 'Inactive';

export async function updateEmployeeLifecycleStatus(employeeId: number, payload: { status: EmployeeLifecycleStatus; effective_date: string; reason: string }): Promise<EmployeeStatusEvent> {
  return request<EmployeeStatusEvent>(`/employees/${employeeId}/status`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export type LifecycleCasePayload = {
  case_type: 'Transfer' | 'Promotion' | 'Resignation';
  effective_date: string;
  reason: string;
  department?: string;
  location?: string;
  manager?: string;
  role?: string;
  new_salary?: string;
  last_working_date?: string;
};

export async function getEmployeeLifecycle(employeeId: number): Promise<EmployeeLifecycle> {
  return request<EmployeeLifecycle>(`/employees/${employeeId}/lifecycle`);
}

export async function createLifecycleCase(employeeId: number, payload: LifecycleCasePayload): Promise<EmployeeLifecycle> {
  return request<EmployeeLifecycle>(`/employees/${employeeId}/lifecycle`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function decideLifecycleCase(caseId: number, status: 'Approved' | 'Rejected'): Promise<void> {
  await request(`/employees/lifecycle/cases/${caseId}/decision`, { method: 'PATCH', body: JSON.stringify({ status }) });
}

export async function updateExitClearance(itemId: number, status: 'Completed' | 'Pending'): Promise<void> {
  await request(`/employees/lifecycle/clearance/${itemId}`, { method: 'PATCH', body: JSON.stringify({ status }) });
}

export async function completeOffboarding(caseId: number): Promise<void> {
  await request(`/employees/lifecycle/cases/${caseId}/complete-offboarding`, { method: 'POST' });
}

export async function recordProbationDecision(employeeId: number, decision: 'Confirmed' | 'Extended', extensionDays = 0, notes = ''): Promise<void> {
  await request(`/employees/${employeeId}/probation`, {
    method: 'POST',
    body: JSON.stringify({ decision, extension_days: extensionDays, notes }),
  });
}

export type OnboardingTask = {
  id: number;
  title: string;
  description: string;
  owner: string;
  status: 'Not started' | 'In progress' | 'Completed';
  due_date: string | null;
  completed_at: string | null;
};

export type OnboardingDetails = {
  employee_id: number;
  phone: string | null;
  start_date: string | null;
  employment_type: string | null;
  emergency_contact_name: string | null;
  emergency_contact_relationship: string | null;
  emergency_contact_phone: string | null;
  progress_percent: number;
  tasks: OnboardingTask[];
};

export async function getEmployeeOnboarding(employeeId: number): Promise<OnboardingDetails> {
  return request<OnboardingDetails>(`/employees/${employeeId}/onboarding`);
}

export async function updateOnboardingTask(taskId: number, status: OnboardingTask['status']): Promise<{ id: number; status: string; completed_at: string | null; employee_status: string | null }> {
  return request<{ id: number; status: string; completed_at: string | null; employee_status: string | null }>(`/employees/onboarding/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

export async function getLeaveRequests(): Promise<LeaveRequestsResponse> {
  return request<LeaveRequestsResponse>('/leave');
}

export async function createLeaveRequest(payload: Omit<LeaveRequest, 'id' | 'status'>): Promise<LeaveRequest> {
  return request<LeaveRequest>('/leave', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateLeaveStatus(requestId: number, status: string): Promise<{ message: string; id: number; status: string }> {
  return request<{ message: string; id: number; status: string }>(`/leave/${requestId}/status?status=${encodeURIComponent(status)}`, {
    method: 'PATCH',
  });
}

export async function cancelLeaveRequest(requestId: number): Promise<{ message: string; id: number; status: string }> {
  return request<{ message: string; id: number; status: string }>(`/leave/${requestId}/cancel`, { method: 'PATCH' });
}

export async function getAttendance(): Promise<AttendanceResponse> {
  return request<AttendanceResponse>('/attendance');
}

export async function checkInAttendance(employeeName: string, employeeEmail: string, location: { latitude: number; longitude: number; accuracy_meters: number }, faceImage: Blob): Promise<{ id: number; employee_name: string; employee_email: string; date: string; check_in: string; check_out: string | null; status: string; notes: string | null }> {
  const body = new FormData();
  body.append('employee_name', employeeName); body.append('employee_email', employeeEmail);
  body.append('date', todayInIndia()); body.append('latitude', String(location.latitude));
  body.append('longitude', String(location.longitude)); body.append('accuracy_meters', String(location.accuracy_meters));
  body.append('face_image', faceImage, 'attendance-face.jpg');
  return request<{ id: number; employee_name: string; employee_email: string; date: string; check_in: string; check_out: string | null; status: string; notes: string | null }>('/attendance/check-in-verified', {
    method: 'POST',
    body,
  });
}

export async function checkOutAttendance(employeeName: string, employeeEmail: string, location: { latitude: number; longitude: number; accuracy_meters: number }, faceImage: Blob): Promise<{ id: number; employee_name: string; employee_email: string; date: string; check_in: string; check_out: string | null; status: string; notes: string | null }> {
  const body = new FormData();
  body.append('employee_name', employeeName); body.append('employee_email', employeeEmail);
  body.append('date', todayInIndia()); body.append('latitude', String(location.latitude));
  body.append('longitude', String(location.longitude)); body.append('accuracy_meters', String(location.accuracy_meters));
  body.append('face_image', faceImage, 'attendance-face.jpg');
  return request<{ id: number; employee_name: string; employee_email: string; date: string; check_in: string; check_out: string | null; status: string; notes: string | null }>('/attendance/check-out-verified', {
    method: 'POST',
    body,
  });
}

export async function monitorAttendanceGeofence(location: { latitude: number; longitude: number; accuracy_meters: number }): Promise<{ state: string; confirmations?: number; grace_ends_at?: string; distance_meters: number }> {
  return request('/attendance/geofence-monitor', {
    method: 'POST',
    body: JSON.stringify({ employee_name: '', employee_email: '', date: todayInIndia(), ...location }),
  });
}

export async function enrollFace(employeeId: number, faceImage: File): Promise<{ status: string; employee_id: number }> {
  const body = new FormData();
  body.append('face_image', faceImage);
  return request(`/attendance/face-enrollment/${employeeId}`, { method: 'POST', body });
}

export type PaidLeaveRow = {
  employee_id: number;
  employee_name: string;
  email: string;
  department: string;
  designation: string;
  date_of_joining: string | null;
  employment_status: 'Probation' | 'Regular';
  employee_status: string;
  monthly_entitlement: number;
  current_month_credit: number;
  opening_balance: number;
  total_credited: number;
  total_taken: number;
  total_unpaid: number;
  remaining_balance: number;
  pending_requests: number;
  utilization_percent: number;
  period_credited: number;
  period_taken: number;
  period_unpaid: number;
  manual_adjustments: number;
  exhausted: boolean;
  overdrawn: boolean;
  never_taken: boolean;
};

export type PaidLeaveReport = {
  period_type: 'month' | 'quarter' | 'financial_year';
  period: string;
  period_start: string;
  period_end: string;
  as_of: string;
  employees: PaidLeaveRow[];
};

export type PaidLeavePolicy = {
  id: number;
  effective_from: string;
  probation_days: number;
  probation_monthly_days: number;
  regular_monthly_days: number;
  paid_leave_types: string[];
  allow_negative_balance: boolean;
};

export type PaidLeaveEmployeeDetails = {
  employee: {
    id: number;
    name: string;
    email: string;
    department: string;
    designation: string;
    employment_status: string;
    date_of_joining: string | null;
    probation_end_date: string | null;
    regular_start_date: string | null;
  };
  period: string;
  balance: PaidLeaveRow;
  ledger: Array<{ id: number; type: string; amount: number; effective_date: string; period: string | null; note: string; created_by: string; created_at: string }>;
  requests: Array<{ id: number; type: string; start_date: string; end_date: string; days: number | null; paid_days: number; unpaid_days: number; is_half_day: boolean; status: string; reason: string }>;
  monthly_history: Array<{ month: string; opening_balance: number; credited: number; carried_forward: number; used: number; unpaid_used: number; reversed: number; adjustments: number; closing_balance: number }>;
};

export type PaidLeaveReportFilters = {
  periodType: 'month' | 'quarter' | 'financial_year';
  period?: string;
  search?: string;
  department?: string;
  designation?: string;
  probationStatus?: string;
  employmentStatus?: string;
  sortBy?: 'employee_name' | 'remaining_balance' | 'utilization' | 'leave_taken';
};

export async function getPaidLeaveReport(filters: PaidLeaveReportFilters): Promise<PaidLeaveReport> {
  const query = new URLSearchParams({ period_type: filters.periodType });
  if (filters.period) query.set('period', filters.period);
  if (filters.search) query.set('search', filters.search);
  if (filters.department) query.set('department', filters.department);
  if (filters.designation) query.set('designation', filters.designation);
  if (filters.probationStatus) query.set('probation_status', filters.probationStatus);
  if (filters.employmentStatus) query.set('employment_status', filters.employmentStatus);
  if (filters.sortBy) query.set('sort_by', filters.sortBy);
  return request<PaidLeaveReport>(`/paid-leave/report?${query.toString()}`);
}

export async function getPaidLeavePolicy(): Promise<PaidLeavePolicy> {
  return request<PaidLeavePolicy>('/paid-leave/policy');
}

export async function updatePaidLeavePolicy(payload: Omit<PaidLeavePolicy, 'id' | 'effective_from'>): Promise<PaidLeavePolicy> {
  return request<PaidLeavePolicy>('/paid-leave/policy', { method: 'PUT', body: JSON.stringify(payload) });
}

export async function getPaidLeaveEmployeeDetails(employeeId: number, periodType: PaidLeaveReportFilters['periodType'], period?: string): Promise<PaidLeaveEmployeeDetails> {
  const query = new URLSearchParams({ period_type: periodType });
  if (period) query.set('period', period);
  return request<PaidLeaveEmployeeDetails>(`/paid-leave/employees/${employeeId}?${query.toString()}`);
}

export async function addPaidLeaveAdjustment(employeeId: number, payload: { amount: number; effective_date: string; reason: string }): Promise<void> {
  await request(`/paid-leave/employees/${employeeId}/adjustments`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function getMyPaidLeaveBalance(): Promise<PaidLeaveRow> {
  return request<PaidLeaveRow>('/paid-leave/me');
}

export type OnboardingModuleData = {
  employee: { id: number; name: string; email: string; department: string; designation: string };
  status: string;
  progress_percent: number;
  mandatory_pending: number;
  overdue_tasks: number;
  tasks: Array<{ id: number; title: string; description: string; owner: string; status: string; due_date: string | null; mandatory?: boolean; comments?: string | null; completed_at: string | null }>;
  documents: Array<{ id: number; title: string; document_type: string; status: string; rejection_reason: string | null; uploaded_at: string }>;
};

export type OnboardingDashboardData = {
  summary: { total: number; preboarding: number; in_progress: number; completed: number; pending_documents: number; overdue_tasks: number };
  employees: Array<{ employee_id: number; employee_name: string; email: string; department: string; designation: string; joining_date: string | null; status: string; progress_percent: number; mandatory_pending: number; documents_pending: number; overdue_tasks: number; deadline: string | null }>;
};

export async function getOnboardingDashboard(): Promise<OnboardingDashboardData> {
  return request<OnboardingDashboardData>('/onboarding/dashboard');
}

export async function getMyOnboarding(): Promise<OnboardingModuleData> {
  return request<OnboardingModuleData>('/onboarding/me');
}

export async function updateMyOnboardingTask(taskId: number, status: string, comments?: string): Promise<void> {
  await request(`/onboarding/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify({ status, comments }) });
}

export async function uploadOnboardingDocument(title: string, documentType: string, file: File): Promise<void> {
  const body = new FormData();
  body.append('title', title);
  body.append('document_type', documentType);
  body.append('file', file);
  await request(`/onboarding/me/documents`, { method: 'POST', body });
}

export async function getLeaveAllocationPreview(requestId: number): Promise<{ requested_days: number; available_paid_days: number; paid_days: number; unpaid_days: number }> {
  return request(`/leave/${requestId}/allocation-preview`);
}
