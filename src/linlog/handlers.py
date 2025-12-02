"""
Log Handlers

Daily rotating file handler with file locking for multi-process safety.
"""

import os
import sys
import time
import logging.handlers
from datetime import datetime


class DailyRotatingHandler(logging.handlers.TimedRotatingFileHandler):
    """
    Daily rotating file handler with multi-process safety

    Rotates log files daily at midnight with naming pattern: app_2024-12-02.log
    Uses file locking to prevent race conditions in multi-process environments (uwsgi, gunicorn).
    """

    def __init__(self, filename, when='midnight', interval=1, backupCount=0,
                 encoding=None, delay=False, utc=False, atTime=None):
        log_dir = os.path.dirname(filename)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        super().__init__(
            filename=filename,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            atTime=atTime
        )

        self._lock_file_path = self.baseFilename + '.lock'

    def _acquire_lock(self):
        """Acquire exclusive lock for file rotation"""
        self._lock_file = open(self._lock_file_path, 'w')

        if sys.platform == 'win32':
            import msvcrt
            msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX)

    def _release_lock(self):
        """Release file rotation lock"""
        if hasattr(self, '_lock_file') and self._lock_file:
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)

            self._lock_file.close()
            self._lock_file = None

    def rotation_filename(self, default_name):
        """Generate filename with date: app_2024-12-02.log"""
        dir_name, base_name = os.path.split(self.baseFilename)
        name_parts = os.path.splitext(base_name)
        base = name_parts[0]
        ext = name_parts[1] if len(name_parts) > 1 else ''
        date_str = datetime.now().strftime('%Y-%m-%d')
        return os.path.join(dir_name, f"{base}_{date_str}{ext}")

    def doRollover(self):
        """
        Perform log rotation with file locking

        Ensures only one process rotates the file at a time,
        preventing race conditions in multi-process environments.
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        try:
            self._acquire_lock()

            current_time = int(time.time())
            new_rollover_at = self.computeRollover(current_time)

            if self.backupCount > 0:
                dfn = self.rotation_filename(
                    self.baseFilename + "." +
                    time.strftime(self.suffix, time.localtime(self.rolloverAt))
                )

                if os.path.exists(self.baseFilename):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(self.baseFilename, dfn)
                    self._delete_old_backups()

            if not self.delay:
                self.stream = self._open()

            self.rolloverAt = new_rollover_at

        finally:
            self._release_lock()

    def _delete_old_backups(self):
        """Keep only the most recent backupCount files"""
        # backupCount=0 means keep all files
        if self.backupCount == 0:
            return

        dir_name, base_name = os.path.split(self.baseFilename)

        if not os.path.exists(dir_name):
            return

        file_names = os.listdir(dir_name)
        base = os.path.splitext(base_name)[0]
        prefix = base + "_"

        result = [os.path.join(dir_name, f) for f in file_names if f.startswith(prefix)]
        result.sort()

        if len(result) > self.backupCount:
            for s in result[:len(result) - self.backupCount]:
                try:
                    os.remove(s)
                except OSError:
                    pass
