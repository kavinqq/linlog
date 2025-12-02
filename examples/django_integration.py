"""
Django/Flask Integration Example

linlog works with any Python logging configuration.
No framework installation required!

Example Django settings.py:
"""

LOGGING_CONFIG_EXAMPLE = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'colored': {
            '()': 'linlog.formatters.ColoredFormatter',
            'format': '[%(asctime)s][%(levelname)s][%(name)s:%(lineno)d]: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'colored'
        },
        'file': {
            'level': 'INFO',
            'class': 'linlog.handlers.DailyRotatingHandler',
            'filename': 'logs/app.log',
            'when': 'midnight',
            'backupCount': 30,
            'formatter': 'colored',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        },
    },
}

if __name__ == '__main__':
    print("Just use linlog classes in your LOGGING dict config!")
    print("No framework dependency needed.")
