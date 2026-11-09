import React from 'react';

type LoginScreenProps = {
  onForgotPassword: () => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  error?: string;
};

type ForgotPasswordScreenProps = {
  onBackToLogin: () => void;
};

export function LoginScreen({ onForgotPassword, onSubmit, error }: LoginScreenProps) {
  return (
    <div className="auth-shell" style={styles.pageShell}>
      <div className="auth-left" style={styles.leftPanel}>
        <div style={styles.brandBlock}>
          <div style={styles.logoCircle}>H</div>
          <div>
            <p style={styles.kicker}>People operations</p>
            <h1 style={styles.brandTitle}>HR Portal</h1>
          </div>
        </div>

        <div style={styles.featureCard}>
          <p style={styles.cardBadge}>Today at a glance</p>
          <h2 style={styles.cardTitle}>Welcome back</h2>
          <div style={styles.statGrid}>
            <div style={styles.statBox}>
              <strong style={styles.statValue}>148</strong>
              <span style={styles.statLabel}>Employees</span>
            </div>
            <div style={styles.statBox}>
              <strong style={styles.statValue}>9</strong>
              <span style={styles.statLabel}>Open roles</span>
            </div>
            <div style={styles.statBox}>
              <strong style={styles.statValue}>96%</strong>
              <span style={styles.statLabel}>Retention</span>
            </div>
          </div>
        </div>
      </div>

      <div className="auth-panel" style={styles.rightPanel}>
        <div className="auth-card" style={styles.formCard}>
          <p style={styles.formEyebrow}>Secure sign in</p>
          <h2 className="auth-heading" style={styles.formTitle}>Access your workspace</h2>

          <form onSubmit={onSubmit} style={styles.form}>
            {error && <div role="alert" className="error-banner" style={styles.formError}>{error}</div>}
            <label style={styles.label}>Work email</label>
            <input
              type="email"
              required
              autoComplete="username"
              style={styles.input}
              placeholder="name@company.com"
            />

            <label style={styles.label}>Password</label>
            <input
              type="password"
              required
              autoComplete="current-password"
              style={styles.input}
              placeholder="Enter your password"
            />

            <div style={styles.rowBetween}>
              <label style={styles.checkboxRow}>
                <input type="checkbox" defaultChecked />
                <span>Remember me</span>
              </label>

              <button
                type="button"
                onClick={onForgotPassword}
                style={styles.linkButton}
              >
                Forgot password?
              </button>
            </div>

            <button type="submit" style={styles.primaryButton}>
              Sign in
            </button>
          </form>

          <p style={styles.footerText}>Need an account or password reset? Contact your HR administrator.</p>
        </div>
      </div>
    </div>
  );
}

export function ForgotPasswordScreen({ onBackToLogin }: ForgotPasswordScreenProps) {
  return (
    <div className="auth-shell" style={styles.pageShell}>
      <div className="auth-left" style={styles.leftPanel}>
        <div style={styles.brandBlock}>
          <div style={styles.logoCircle}>H</div>
          <div>
            <p style={styles.kicker}>Reset access</p>
            <h1 style={styles.brandTitle}>HR Portal</h1>
          </div>
        </div>

        <div style={styles.featureCard}>
          <p style={styles.cardBadge}>Account recovery</p>
          <h2 style={styles.cardTitle}>Need help signing in?</h2>
          <p style={styles.infoText}>
            Self-service reset email is not configured yet. Contact your HR administrator to restore account access.
          </p>
        </div>
      </div>

      <div className="auth-panel" style={styles.rightPanel}>
        <div className="auth-card" style={styles.formCard}>
          <p style={styles.formEyebrow}>Password reset</p>
          <h2 className="auth-heading" style={styles.formTitle}>Recover your account</h2>

          <button type="button" onClick={onBackToLogin} style={styles.secondaryTextButton}>
            ← Back to sign in
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  pageShell: {
    minHeight: '100vh',
    display: 'flex',
    background: 'linear-gradient(135deg, #f3f7ff 0%, #eef2ff 100%)',
    fontFamily: 'Inter, Arial, sans-serif',
    color: '#111827',
  },
  leftPanel: {
    flex: 1,
    padding: '60px 40px',
    background: 'linear-gradient(180deg, #0f172a 0%, #111827 100%)',
    color: '#f8fafc',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
  },
  brandBlock: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  logoCircle: {
    width: '52px',
    height: '52px',
    borderRadius: '16px',
    background: 'linear-gradient(135deg, #60a5fa, #8b5cf6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '1.5rem',
    fontWeight: 700,
  },
  kicker: {
    margin: 0,
    fontSize: '0.76rem',
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
    opacity: 0.75,
  },
  brandTitle: {
    margin: '4px 0 0',
    fontSize: '2rem',
  },
  featureCard: {
    background: 'rgba(148, 163, 184, 0.12)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '24px',
    padding: '28px',
    maxWidth: '420px',
  },
  cardBadge: {
    margin: 0,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: '#cbd5e1',
    fontSize: '0.7rem',
  },
  cardTitle: {
    margin: '12px 0 20px',
    fontSize: '2rem',
  },
  statGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
    gap: '12px',
  },
  statBox: {
    background: 'rgba(15, 23, 42, 0.55)',
    borderRadius: '16px',
    padding: '16px 12px',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  statValue: {
    fontSize: '1.3rem',
  },
  statLabel: {
    fontSize: '0.72rem',
    color: '#cbd5e1',
  },
  rightPanel: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '32px',
    background: '#f8fafc',
  },
  formCard: {
    width: '100%',
    maxWidth: '480px',
    background: '#ffffff',
    borderRadius: '24px',
    padding: '36px',
    boxShadow: '0 24px 70px rgba(15, 23, 42, 0.08)',
    border: '1px solid rgba(148, 163, 184, 0.18)',
  },
  formEyebrow: {
    margin: 0,
    fontSize: '0.72rem',
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: '#6366f1',
    fontWeight: 700,
  },
  formTitle: {
    margin: '10px 0 24px',
    fontSize: '2rem',
    lineHeight: 1.2,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  formError: { padding: '11px 13px', borderRadius: '10px', color: '#991b1b', background: '#fff1f2', fontSize: '.84rem', lineHeight: 1.45 },
  label: {
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#374151',
  },
  input: {
    width: '100%',
    padding: '14px 16px',
    borderRadius: '12px',
    border: '1px solid #dbe2f0',
    fontSize: '0.98rem',
    outline: 'none',
    boxSizing: 'border-box',
    background: '#f8fafc',
  },
  rowBetween: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    marginTop: '4px',
  },
  checkboxRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '0.8rem',
    color: '#4b5563',
  },
  linkButton: {
    border: 'none',
    background: 'transparent',
    color: '#4f46e5',
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: '0.8rem',
  },
  primaryButton: {
    marginTop: '8px',
    border: 'none',
    borderRadius: '12px',
    padding: '15px 18px',
    background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
    color: '#ffffff',
    fontSize: '0.96rem',
    fontWeight: 700,
    cursor: 'pointer',
    boxShadow: '0 12px 28px rgba(79, 70, 229, 0.25)',
  },
  dividerRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    margin: '26px 0 18px',
    color: '#94a3b8',
    fontSize: '0.75rem',
  },
  dividerLine: {
    flex: 1,
    height: '1px',
    background: '#e2e8f0',
  },
  dividerText: {
    whiteSpace: 'nowrap',
  },
  secondaryActions: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: '12px',
  },
  secondaryButton: {
    border: '1px solid #dfe7f4',
    borderRadius: '12px',
    padding: '12px 14px',
    background: '#fff',
    fontWeight: 600,
    cursor: 'pointer',
    color: '#1f2937',
  },
  footerText: {
    margin: '22px 0 0',
    textAlign: 'center',
    color: '#6b7280',
    fontSize: '0.82rem',
  },
  highlightText: {
    color: '#4f46e5',
    fontWeight: 700,
  },
  infoText: {
    color: '#cbd5e1',
    lineHeight: 1.7,
    marginTop: '12px',
  },
  secondaryTextButton: {
    marginTop: '18px',
    border: 'none',
    background: 'transparent',
    color: '#4f46e5',
    fontWeight: 700,
    cursor: 'pointer',
    fontSize: '0.9rem',
    alignSelf: 'flex-start',
  },
};
