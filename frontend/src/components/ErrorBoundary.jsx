import React from 'react';
import { RefreshCw } from 'lucide-react';

// If a screen crashes, show a friendly message instead of a blank white page, and tell the server
// what broke (message and where, nothing personal) so it can be fixed.
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error, info) {
    try {
      fetch('/api/client-error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: String(error?.message || error).slice(0, 500),
          where: String(info?.componentStack || error?.stack || '').slice(0, 2000),
          page: window.location.pathname,
        }),
      }).catch(() => {});
    } catch { /* reporting is best-effort */ }
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="crash" role="alert">
        <img src="/brand/peheraav-mark.svg" alt="" />
        <h1>Something went wrong</h1>
        <p>Sorry, this screen hit a problem. Your wardrobe and looks are safe. Reloading usually fixes it.</p>
        <button type="button" className="primary" onClick={() => window.location.reload()}><RefreshCw size={15} /> Reload Peheraav</button>
      </div>
    );
  }
}
