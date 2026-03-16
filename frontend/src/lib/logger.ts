type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogContext extends Record<string, unknown> {
  request_id?: string
  timestamp?: string
  level?: string
  message?: string
}

interface Logger {
  debug(message: string, context?: Record<string, unknown>): void
  info(message: string, context?: Record<string, unknown>): void
  warn(message: string, context?: Record<string, unknown>): void
  error(message: string, context?: Record<string, unknown>): void
}

const isProduction = process.env.NODE_ENV === 'production'

function formatTimestamp(): string {
  return new Date().toISOString()
}

function createLogEntry(
  level: LogLevel,
  message: string,
  context?: Record<string, unknown>
): Record<string, unknown> {
  return {
    timestamp: formatTimestamp(),
    level,
    message,
    ...context,
  }
}

function logToConsole(
  level: LogLevel,
  message: string,
  context?: Record<string, unknown>
): void {
  const entry = createLogEntry(level, message, context)

  if (isProduction) {
    // JSON line format for production
    console.log(JSON.stringify(entry))
  } else {
    // Colored format for development
    const timestamp = entry.timestamp as string
    const contextStr = context && Object.keys(context).length > 0
      ? ` ${JSON.stringify(context)}`
      : ''

    const prefix = `[${timestamp}] [${level.toUpperCase()}]`
    const logMessage = `${prefix} ${message}${contextStr}`

    switch (level) {
      case 'debug':
        console.debug(logMessage)
        break
      case 'info':
        console.log(logMessage)
        break
      case 'warn':
        console.warn(logMessage)
        break
      case 'error':
        console.error(logMessage)
        break
    }
  }
}

const createLogger = (baseContext?: Record<string, unknown>): Logger => ({
  debug(message: string, context?: Record<string, unknown>): void {
    logToConsole('debug', message, { ...baseContext, ...context })
  },
  info(message: string, context?: Record<string, unknown>): void {
    logToConsole('info', message, { ...baseContext, ...context })
  },
  warn(message: string, context?: Record<string, unknown>): void {
    logToConsole('warn', message, { ...baseContext, ...context })
  },
  error(message: string, context?: Record<string, unknown>): void {
    logToConsole('error', message, { ...baseContext, ...context })
  },
})

export const logger = createLogger()

export function withRequestId(requestId: string): Logger {
  return createLogger({ request_id: requestId })
}
