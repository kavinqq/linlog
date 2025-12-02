# linlog

Simple Python logging utilities with daily rotation and UUID tracking.

## Features

- **StandardFormatter**: Clean, consistent log format `[time][level][name:line]message`
- **DailyRotatingHandler**: Automatic daily log rotation with custom naming (`app_2024-12-02.log`)
- **UUIDFilter**: Track requests across multiple log entries with unique IDs
- **Multi-process safe**: File locking prevents race conditions (uwsgi, gunicorn)
- **Zero dependencies**: Uses only Python standard library

## Installation

```bash
pip install linlog
```

Or install from source:
```bash
git clone https://github.com/yourusername/linlog.git
cd linlog
pip install -e .
```

## Quick Start

### Basic Usage

```python
import logging
from linlog import StandardFormatter, DailyRotatingHandler

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handler with daily rotation
handler = DailyRotatingHandler(
    filename='logs/app.log',
    when='midnight',
    backupCount=30,  # Keep 30 days of logs
    encoding='utf-8'
)

# Set formatter
handler.setFormatter(StandardFormatter())
logger.addHandler(handler)

# Use logger
logger.info("Application started")
logger.error("Something went wrong")
```

Output:
```
[2024-12-02 14:23:45][INFO][__main__:15]Application started
[2024-12-02 14:23:46][ERROR][__main__:16]Something went wrong
```

### Django Integration

See [USAGE_EXAMPLE.md](USAGE_EXAMPLE.md) for complete Django setup with UUID tracking.

#### settings.py
```python
LOGGING = {
    'version': 1,
    'formatters': {
        'standard': {
            '()': 'linlog.formatters.StandardFormatter',
        },
    },
    'handlers': {
        'file': {
            'class': 'linlog.handlers.DailyRotatingHandler',
            'filename': 'logs/app.log',
            'when': 'midnight',
            'backupCount': 30,
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

## Components

### StandardFormatter

Formats logs in a clean, consistent style:
```
[2024-12-02 14:23:45][INFO][module.name:98]message content
```

### DailyRotatingHandler

- Rotates logs daily at midnight
- Custom naming: `app_2024-12-02.log`
- Auto-cleanup: keeps only N days of logs
- Multi-process safe with file locking

### UUIDFilter

Track all logs from the same request:

```python
from linlog import UUIDFilter, set_request_id
import uuid

# In middleware
set_request_id(str(uuid.uuid4()))

# Add filter to handler
handler.addFilter(UUIDFilter())
```

All logs will include `record.request_id` for correlation.

## Requirements

- Python 3.8+
- No external dependencies

## Production Use

### Multi-process environments (uwsgi, gunicorn)

linlog uses file locking to prevent race conditions during log rotation:

```ini
[uwsgi]
processes=10        #  Safe
threads=4           #  Safe
enable-threads=true
```

All processes can safely write to the same log file.

## API Reference

### Formatters

#### StandardFormatter(datefmt='%Y-%m-%d %H:%M:%S')
Standard log formatter with customizable date format.

#### JSONFormatter()
JSON format for machine parsing and log analysis tools.

### Handlers

#### DailyRotatingHandler(filename, when='midnight', backupCount=0, ...)
Daily rotating file handler with multi-process safety.

Parameters:
- `filename`: Log file path
- `when`: Rotation interval ('midnight', 'H', 'D')
- `backupCount`: Number of backup files to keep (0 = keep all)
- `encoding`: File encoding (default: utf-8)

### Filters

#### UUIDFilter()
Adds request UUID to log records as `record.request_id`.

### Context Management

#### set_request_id(request_id: str)
Set UUID for current request context.

#### get_request_id() -> str | None
Get UUID from current request context.

#### clear_request_id()
Clear UUID after request completes.

## License

MIT

## Author

Kuan Lin
