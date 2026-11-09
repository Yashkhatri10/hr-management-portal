import type { ReactNode } from 'react';

type LayoutProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function Layout({ title, subtitle, actions, children, className = '' }: LayoutProps) {
  return (
    <div className={`page-layout ${className}`.trim()} style={styles.wrapper}>
      <header className="page-header" style={styles.header}>
        <div>
          <p className="page-subtitle" style={styles.subtitle}>{subtitle || 'Overview'}</p>
          <h1 className="page-title" style={styles.title}>{title}</h1>
        </div>
        {actions}
      </header>
      {children}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    background: '#f8fafc',
    fontFamily: 'Inter, Arial, sans-serif',
    color: '#0f172a',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '20px',
    gap: '12px',
  },
  subtitle: {
    margin: 0,
    fontSize: '0.75rem',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: '#64748b',
  },
  title: {
    margin: '8px 0 0',
    fontSize: '2rem',
  },
};
