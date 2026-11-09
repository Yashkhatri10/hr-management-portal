import { useEffect, useRef, useState } from 'react';
import { Layout } from '../components/Layout';
import { checkInAttendance, checkOutAttendance, downloadReport, enrollFace, getAttendance, monitorAttendanceGeofence } from '../services/api';
import type { AttendanceRecord, AttendanceSummary, User } from '../types';

export function AttendancePage({ user }: { user: User }) {
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [summary, setSummary] = useState<AttendanceSummary>({
    present: 0,
    late: 0,
    absent: 0,
    attendanceRate: 0,
  });
  const [loading, setLoading] = useState(false);
  const [actionError, setActionError] = useState('');
  const [exporting, setExporting] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [geofenceStatus, setGeofenceStatus] = useState('');
  const [enrollmentEmployeeId, setEnrollmentEmployeeId] = useState('');
  const [enrollmentFile, setEnrollmentFile] = useState<File | null>(null);
  const [enrollmentMessage, setEnrollmentMessage] = useState('');
  const videoRef = useRef<HTMLVideoElement>(null);

  const loadAttendance = async () => {
    setLoading(true);
    try {
      const response = await getAttendance();
      setRecords(response.records);
      setSummary(response.summary);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAttendance();
  }, []);

  useEffect(() => {
    const active = records.some((record) => record.employee_email === user.email && record.check_in && !record.check_out);
    if (!active || !navigator.geolocation) {
      setGeofenceStatus('');
      return undefined;
    }
    const monitor = () => {
      navigator.geolocation.getCurrentPosition(async (position) => {
        try {
          const result = await monitorAttendanceGeofence({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy_meters: position.coords.accuracy,
          });
          setGeofenceStatus(result.state === 'grace_period' || result.state === 'confirming_exit'
            ? `You are outside the permitted area. Automatic checkout status: ${result.state.replace('_', ' ')}.`
            : result.state === 'auto_checked_out' ? 'Automatic checkout completed after leaving the permitted area.' : '');
          if (result.state === 'auto_checked_out') await loadAttendance();
        } catch {
          // Monitoring is best effort; manual attendance errors remain visible separately.
        }
      }, () => undefined, { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
    };
    monitor();
    const interval = window.setInterval(monitor, 30000);
    return () => window.clearInterval(interval);
  }, [records, user.email]);

  const getFreshLocation = (): Promise<{ latitude: number; longitude: number; accuracy_meters: number }> => new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('This browser does not support location services.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude, accuracy_meters: position.coords.accuracy }),
      (error) => reject(new Error(error.code === error.PERMISSION_DENIED ? 'Location permission was denied. Enable location access and try again.' : error.code === error.TIMEOUT ? 'Location lookup timed out. Move to an area with a stronger GPS signal and retry.' : 'Location is unavailable. Enable device location services and retry.')),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  });

  const handleAttendanceAction = async (action: 'in' | 'out') => {
    setActionError('');
    setLocationLoading(true);
    try {
      const location = await getFreshLocation();
      const faceImage = await captureFaceImage();
      if (action === 'in') await checkInAttendance(user.name, user.email, location, faceImage);
      else await checkOutAttendance(user.name, user.email, location, faceImage);
      await loadAttendance();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : `Unable to check ${action === 'in' ? 'in' : 'out'}.`);
    } finally {
      setLocationLoading(false);
    }
  };

  const captureFaceImage = async (): Promise<Blob> => {
    if (!navigator.mediaDevices?.getUserMedia || !videoRef.current) {
      throw new Error('Camera access is unavailable. Use HTTPS or localhost and allow camera access.');
    }
    setCameraOpen(true);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
    } catch (error) {
      setCameraOpen(false);
      throw new Error(error instanceof DOMException && error.name === 'NotAllowedError' ? 'Camera permission was denied. Allow camera access and try again.' : 'Unable to access the camera.');
    }
    const video = videoRef.current;
    video.srcObject = stream;
    try {
      await video.play();
      await new Promise((resolve) => window.setTimeout(resolve, 700));
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      if (!canvas.width || !canvas.height) throw new Error('Camera did not provide a usable image.');
      canvas.getContext('2d')?.drawImage(video, 0, 0);
      return await new Promise<Blob>((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error('Unable to capture a face image.')), 'image/jpeg', 0.9));
    } finally {
      stream.getTracks().forEach((track) => track.stop());
      video.srcObject = null;
      setCameraOpen(false);
    }
  };

  const exportAttendance = async (format: 'csv' | 'xlsx' | 'pdf') => {
    setActionError('');
    setExporting(true);
    try {
      await downloadReport('attendance', format);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Unable to export attendance.');
    } finally {
      setExporting(false);
    }
  };

  const submitEnrollment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!enrollmentEmployeeId || !enrollmentFile) {
      setEnrollmentMessage('Choose an employee ID and a clear image containing exactly one face.');
      return;
    }
    try {
      const result = await enrollFace(Number(enrollmentEmployeeId), enrollmentFile);
      setEnrollmentMessage(`Face enrolled for employee ${result.employee_id}.`);
      setEnrollmentFile(null);
    } catch (error) {
      setEnrollmentMessage(error instanceof Error ? error.message : 'Face enrollment failed.');
    }
  };

  return (
    <Layout title="Attendance" subtitle="Time tracking" actions={<div style={{ display: 'flex', gap: '8px' }}>
      <button type="button" className="primary-action" style={styles.primaryButton} disabled={exporting} onClick={() => void exportAttendance('csv')}>Export CSV</button>
      <button type="button" className="secondary-action" disabled={exporting} onClick={() => void exportAttendance('xlsx')}>Export Excel</button>
      <button type="button" className="secondary-action" disabled={exporting} onClick={() => void exportAttendance('pdf')}>Export PDF</button>
    </div>}>
      <div style={styles.actionRow}>
        <button type="button" onClick={() => void handleAttendanceAction('in')} disabled={loading || locationLoading} className="primary-action" style={{ ...styles.primaryButton, marginRight: '12px' }}>{locationLoading ? 'Locating…' : 'Check in'}</button>
        <button type="button" onClick={() => void handleAttendanceAction('out')} disabled={loading || locationLoading} className="secondary-action" style={{ ...styles.secondaryButton }}>{locationLoading ? 'Locating…' : 'Check out'}</button>
      </div>
      {actionError && <p role="alert" className="error-banner" style={styles.error}>{actionError}</p>}
      {geofenceStatus && <p role="status" style={styles.warning}>{geofenceStatus}</p>}
      {user.role === 'HR Manager' && <form onSubmit={(event) => void submitEnrollment(event)} style={styles.enrollment}>
        <strong>Face enrollment</strong>
        <input aria-label="Employee ID for face enrollment" type="number" min="1" value={enrollmentEmployeeId} onChange={(event) => setEnrollmentEmployeeId(event.target.value)} placeholder="Employee ID" />
        <input aria-label="Face image" type="file" accept="image/*" capture="user" onChange={(event) => setEnrollmentFile(event.target.files?.[0] || null)} />
        <button type="submit" className="secondary-action">Enroll or replace template</button>
        {enrollmentMessage && <span role="status">{enrollmentMessage}</span>}
      </form>}
      <video ref={videoRef} muted playsInline aria-label="Live face capture preview" style={{ ...styles.camera, display: cameraOpen ? 'block' : 'none' }} />

      <section style={styles.summaryGrid}>
        <div style={styles.summaryCard}>
          <span style={styles.cardLabel}>Present</span>
          <strong style={styles.cardValue}>{summary.present}</strong>
        </div>
        <div style={styles.summaryCard}>
          <span style={styles.cardLabel}>Late</span>
          <strong style={styles.cardValue}>{summary.late}</strong>
        </div>
        <div style={styles.summaryCard}>
          <span style={styles.cardLabel}>Absent</span>
          <strong style={styles.cardValue}>{summary.absent}</strong>
        </div>
        <div style={styles.summaryCard}>
          <span style={styles.cardLabel}>Attendance</span>
          <strong style={styles.cardValue}>{summary.attendanceRate}%</strong>
        </div>
      </section>

      <div className="surface-card" style={styles.tableCard}>
        <h3 style={styles.sectionTitle}>Daily attendance log</h3>
        {loading ? (
          <p>Loading attendance...</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Employee</th>
                <th style={styles.th}>Date</th>
                <th style={styles.th}>Check-in</th>
                <th style={styles.th}>Check-out</th>
                <th style={styles.th}>Status</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id}>
                  <td style={styles.td}>{record.employee_name}</td>
                  <td style={styles.td}>{record.date}</td>
                  <td style={styles.td}>{record.check_in || '—'}</td>
                  <td style={styles.td}>{record.check_out || '—'}</td>
                  <td style={styles.td}>
                    <span style={{ ...styles.statusPill, background: record.status === 'Present' ? '#dcfce7' : record.status === 'Late' ? '#fef3c7' : '#fee2e2', color: record.status === 'Present' ? '#166534' : record.status === 'Late' ? '#92400e' : '#991b1b' }}>
                      {record.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
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
  tableCard: {
    background: '#fff',
    borderRadius: '20px',
    padding: '22px',
    border: '1px solid #e2e8f0',
  },
  sectionTitle: {
    marginTop: 0,
    marginBottom: '18px',
    fontSize: '1.2rem',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    textAlign: 'left',
    padding: '10px 12px',
    borderBottom: '1px solid #e2e8f0',
    color: '#475569',
    fontSize: '0.8rem',
  },
  td: {
    padding: '12px',
    borderBottom: '1px solid #eef2f7',
    color: '#0f172a',
  },
  actionRow: {
    display: 'flex',
    gap: '12px',
    marginBottom: '20px',
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
  secondaryButton: {
    background: '#0f172a',
    color: '#fff',
    border: 'none',
    borderRadius: '12px',
    padding: '12px 16px',
    fontWeight: 700,
    cursor: 'pointer',
  },
  camera: {
    width: 'min(100%, 360px)',
    borderRadius: '14px',
    marginBottom: '16px',
    background: '#0f172a',
  },
  statusPill: {
    display: 'inline-flex',
    padding: '6px 10px',
    borderRadius: '999px',
    fontSize: '0.75rem',
    fontWeight: 700,
  },
  error: { padding: '12px', borderRadius: '10px', background: '#fee2e2', color: '#991b1b' },
  warning: { padding: '12px', borderRadius: '10px', background: '#fef3c7', color: '#92400e' },
  enrollment: {
    display: 'flex',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '10px',
    marginBottom: '20px',
    padding: '14px',
    borderRadius: '12px',
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
  },
};
