"""
Log Handlers

Daily rotating file handler with file locking for multi-process safety.
"""

import os
import re
import sys
import time
import logging.handlers
from datetime import datetime, timedelta


class DailyRotatingHandler(logging.handlers.TimedRotatingFileHandler):
    """
    Daily rotating file handler with multi-process safety

    Rotates log files daily at midnight with naming pattern: app.log.2024-12-02
    Uses file locking to prevent race conditions in multi-process environments (uwsgi, gunicorn).
    
    Key difference from standard TimedRotatingFileHandler:
    - Uses file's mtime (last modification time) to determine archive date
    - NOT rolloverAt, which can be stale in multi-process/restart scenarios
    
    Args:
        filename_pattern: Format string for rotated files. Available placeholders:
            - {base}: filename without extension (e.g., "debug")
            - {ext}: file extension with dot (e.g., ".log")  
            - {date}: date string (e.g., "2025-12-02")
            
            Examples:
            - "{base}{ext}.{date}" → debug.log.2025-12-02 (default, Linux style)
            - "{base}_{date}{ext}" → debug_2025-12-02.log
    """

    def __init__(self, filename, when='midnight', interval=1, backupCount=180,
                 encoding=None, delay=False, utc=False, atTime=None,
                 filename_pattern="{base}{ext}.{date}"):
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
        self._lock_file = None
        self.filename_pattern = filename_pattern

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
        if self._lock_file:
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)

            self._lock_file.close()
            self._lock_file = None

    def _get_file_date(self):
        """
        Get the date the current log file belongs to, based on its mtime.
        
        This is THE source of truth for determining which day's log this file contains.
        """
        if not os.path.exists(self.baseFilename):
            return None
            
        try:
            mtime = os.path.getmtime(self.baseFilename)
            if self.utc:
                return datetime.fromtimestamp(mtime, datetime.timezone.utc).date()
            else:
                return datetime.fromtimestamp(mtime).date()
        except (OSError, ValueError):
            return None

    def _get_today(self):
        """Get today's date."""
        if self.utc:
            return datetime.now(datetime.timezone.utc).date()
        else:
            return datetime.now().date()

    def _build_archive_filename(self, archive_date):
        """
        Build the archive filename for a given date.
        
        Args:
            archive_date: The date to use for the archive filename (date object)
            
        Returns:
            Full path to the archive file
        """
        dir_name, base_name = os.path.split(self.baseFilename)
        name_parts = os.path.splitext(base_name)
        base = name_parts[0]
        ext = name_parts[1] if len(name_parts) > 1 else ''
        
        date_str = archive_date.strftime('%Y-%m-%d')
        rotated_name = self.filename_pattern.format(base=base, ext=ext, date=date_str)
        return os.path.join(dir_name, rotated_name)

    def rotation_filename(self, default_name):
        """
        Generate filename for rotation.
        
        This method is called by the parent class. We override it to use
        our mtime-based date calculation instead of rolloverAt.
        """
        file_date = self._get_file_date()
        if file_date is None:
            # No file exists, use yesterday as fallback
            file_date = self._get_today() - timedelta(days=1)
            
        return self._build_archive_filename(file_date)

    def shouldRollover(self, record):
        """
        Determine if rollover should occur.
        
        We check if the current log file is from a previous day.
        This is more reliable than checking rolloverAt in multi-process environments.
        """
        if self.stream is None:
            self.stream = self._open()
            
        file_date = self._get_file_date()
        if file_date is None:
            return False
            
        today = self._get_today()
        return file_date < today

    def doRollover(self):
        """
        Perform log rotation with file locking.
        
        Key logic:
        1. Use file's mtime to determine which date the log belongs to
        2. Archive to that date (not rolloverAt - 1 day)
        3. Check for race conditions before renaming
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        try:
            self._acquire_lock()

            # Re-check after acquiring lock (another process may have rotated already)
            file_date = self._get_file_date()
            today = self._get_today()
            
            # If file doesn't exist or is already from today, skip rotation
            if file_date is None or file_date >= today:
                # Just open a new stream and update rolloverAt
                current_time = int(time.time())
                self.rolloverAt = self.computeRollover(current_time)
                if not self.delay:
                    self.stream = self._open()
                return

            # Calculate archive filename based on file's mtime (THE TRUTH)
            dfn = self._build_archive_filename(file_date)

            # Check if archive already exists (race condition protection)
            should_rotate = True
            if os.path.exists(dfn):
                if os.path.getsize(dfn) > 0:
                    # Archive already exists with content - someone else did it
                    should_rotate = False
                else:
                    # Empty file - safe to remove and retry
                    try:
                        os.remove(dfn)
                    except OSError:
                        pass

            # Perform the actual rotation
            if should_rotate and os.path.exists(self.baseFilename):
                # Final safety check: is the file STILL from a previous day?
                current_file_date = self._get_file_date()
                if current_file_date is not None and current_file_date < today:
                    try:
                        os.rename(self.baseFilename, dfn)
                    except OSError:
                        pass

            # Delete old backups
            if self.backupCount > 0:
                self._delete_old_backups()

            # Update rollover time for next check
            current_time = int(time.time())
            self.rolloverAt = self.computeRollover(current_time)

            if not self.delay:
                self.stream = self._open()

        finally:
            self._release_lock()

    def _delete_old_backups(self):
        """Keep only the most recent backupCount files"""
        if self.backupCount == 0:
            return

        dir_name, base_name = os.path.split(self.baseFilename)

        if not dir_name:
            dir_name = '.'
            
        if not os.path.exists(dir_name):
            return

        # Build regex pattern from filename_pattern
        name_parts = os.path.splitext(base_name)
        base = name_parts[0]
        ext = name_parts[1] if len(name_parts) > 1 else ''
        
        pattern_str = self.filename_pattern.format(
            base=re.escape(base),
            ext=re.escape(ext),
            date=r'\d{4}-\d{2}-\d{2}'
        )
        pattern = re.compile(f'^{pattern_str}$')
        
        file_names = os.listdir(dir_name)
        result = [os.path.join(dir_name, f) for f in file_names if pattern.match(f)]
        result.sort()

        if len(result) > self.backupCount:
            for s in result[:len(result) - self.backupCount]:
                try:
                    os.remove(s)
                except OSError:
                    pass
