export type User = {
  id: number;
  name: string;
  email: string;
  role: string;
};

export type LoginResponse = {
  token: string;
  user: User;
};

export type Employee = {
  id: number;
  name: string;
  email: string;
  role: string;
  department: string;
  location: string;
  status: 'Active' | 'On Notice' | 'On Leave' | 'Pending' | 'Terminated' | 'Inactive';
  manager: string;
  phone?: string | null;
  start_date?: string | null;
};

export type DashboardSummary = {
  totalEmployees: number;
  openPositions: number;
  attendance: number;
  pendingTasks: number;
  leaveBalance: number;
  upcomingLeaves: number;
  usedLeaves: number;
};

export type DashboardData = {
  summary: DashboardSummary;
  recentActivity: string[];
  upcomingHires: string[];
  upcomingLeaveSchedule: string[];
};

export type EmployeesResponse = {
  employees: Employee[];
};

export type LeaveRequest = {
  id: number;
  employee_name: string;
  employee_email: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: string;
  is_half_day?: boolean;
  paid_days?: number;
  unpaid_days?: number;
};

export type LeaveRequestsResponse = {
  requests: LeaveRequest[];
};

export type AttendanceRecord = {
  id: number;
  employee_name: string;
  employee_email: string;
  date: string;
  check_in: string | null;
  check_out: string | null;
  status: string;
  notes: string | null;
};

export type AttendanceSummary = {
  present: number;
  late: number;
  absent: number;
  attendanceRate: number;
};

export type AttendanceResponse = {
  records: AttendanceRecord[];
  summary: AttendanceSummary;
};
