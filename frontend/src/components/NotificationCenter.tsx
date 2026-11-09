import { useCallback, useEffect, useState } from 'react';
import {
  getNotificationModuleCounts, getNotificationUnreadCount, getNotifications,
  markAllNotificationsRead, markNotificationRead, type NotificationItem,
} from '../services/api';

type Props = { onNavigate: (module: string, link: string | null) => void; onCountsChange: (counts: Record<string, number>) => void };

export function NotificationCenter({ onNavigate, onCountsChange }: Props) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      const [list, count, modules] = await Promise.all([getNotifications(), getNotificationUnreadCount(), getNotificationModuleCounts()]);
      setItems(list.notifications);
      setUnread(count.count);
      onCountsChange(modules.counts);
      setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load notifications.');
    }
  }, [onCountsChange]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 12000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const read = async (item: NotificationItem) => {
    if (!item.is_read) await markNotificationRead(item.id);
    setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, is_read: true } : entry));
    setUnread((value) => Math.max(0, value - (item.is_read ? 0 : 1)));
    await refresh();
    onNavigate(item.module, item.action_link);
    setOpen(false);
  };

  const readAll = async () => {
    await markAllNotificationsRead();
    await refresh();
  };

  return <div style={{ position: 'relative' }}>
    <button type="button" aria-label="Notifications" onClick={() => setOpen((value) => !value)} style={styles.bell}>
      <span aria-hidden="true">🔔</span>{unread > 0 && <span style={styles.badge}>{unread > 99 ? '99+' : unread}</span>}
    </button>
    {open && <div style={styles.panel}>
      <div style={styles.panelHeader}><strong>Notifications</strong><button type="button" onClick={() => void readAll()} disabled={!unread} style={styles.link}>Mark all read</button></div>
      {error && <p style={styles.error}>{error}</p>}
      {!error && items.length === 0 && <p style={styles.empty}>You have no notifications.</p>}
      <div style={styles.list}>{items.map((item) => <button key={item.id} type="button" onClick={() => void read(item)} style={{ ...styles.item, background: item.is_read ? '#fff' : '#eef2ff' }}><strong>{item.title}</strong><span>{item.message}</span><small>{item.module} · {new Date(item.created_at).toLocaleString()}</small></button>)}</div>
    </div>}
  </div>;
}

const styles: Record<string, React.CSSProperties> = {
  bell: { position: 'relative', border: '1px solid #dbe3ef', background: '#fff', borderRadius: 10, padding: '9px 12px', cursor: 'pointer', fontSize: 18 },
  badge: { position: 'absolute', top: -7, right: -7, minWidth: 18, height: 18, padding: '0 4px', borderRadius: 9, background: '#dc2626', color: '#fff', fontSize: 10, fontWeight: 800, lineHeight: '18px' },
  panel: { position: 'absolute', zIndex: 20, right: 0, top: 46, width: 'min(380px, calc(100vw - 32px))', maxHeight: 480, overflow: 'auto', background: '#fff', border: '1px solid #dbe3ef', borderRadius: 14, boxShadow: '0 14px 35px rgba(15,23,42,.16)' },
  panelHeader: { display: 'flex', justifyContent: 'space-between', padding: 14, borderBottom: '1px solid #e2e8f0' },
  link: { border: 0, background: 'none', color: '#4f46e5', cursor: 'pointer', fontWeight: 700 },
  list: { display: 'grid' },
  item: { display: 'grid', gap: 4, padding: 13, border: 0, borderBottom: '1px solid #eef2f7', textAlign: 'left', cursor: 'pointer' },
  empty: { padding: 18, color: '#64748b' },
  error: { padding: 12, margin: 0, color: '#991b1b', background: '#fee2e2' },
};
