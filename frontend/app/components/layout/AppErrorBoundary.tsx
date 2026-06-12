import React from 'react'

interface AppErrorBoundaryProps {
  children: React.ReactNode
}

interface AppErrorBoundaryState {
  hasError: boolean
}

export default class AppErrorBoundary extends React.Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: unknown, errorInfo: unknown) {
    console.error('HyperAlpha UI render failure', { error, errorInfo })
  }

  private reloadApp = () => {
    window.location.reload()
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-4">
        <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <div className="space-y-2">
            <h1 className="text-lg font-semibold">Hyper Alpha Arena</h1>
            <p className="text-sm text-muted-foreground">
              The app recovered from a UI loading error. Reload the page to continue.
            </p>
          </div>
          <button
            type="button"
            onClick={this.reloadApp}
            className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 text-xs font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            Reload app
          </button>
        </div>
      </div>
    )
  }
}
