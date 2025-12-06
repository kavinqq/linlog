"""
Log Handlers

Daily rotating file handler with multi-process safety using optimistic locking.
"""

import os
import re
import time
import logging.handlers
from datetime import datetime, timedelta


class DailyRotatingHandler(logging.handlers.TimedRotatingFileHandler):
    """
    Daily rotating file handler with multi-process safety

    Rotates log files daily at midnight with naming pattern: debug.log.2024-12-02 (Ubuntu style)
    Uses optimistic locking (atomic rename + exception handling) for multi-process safety.
    
    Key features:
    - Uses file's mtime (last modification time) to determine archive date
    - Uses atomic os.rename() + exception handling instead of file locks
    - Automatically detects when another process has already rotated
    
    Args:
        filename_pattern: Format string for rotated files. Available placeholders:
            - {base}: filename without extension (e.g., "debug")
            - {ext}: file extension with dot (e.g., ".log")  
            - {date}: date string (e.g., "2025-12-02")
            
            Examples:
            - "{base}{ext}.{date}" → debug.log.2025-12-02 (default, Ubuntu/Linux style)
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

        self.filename_pattern = filename_pattern

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
            Full path to the archive file (e.g., /var/log/debug.log.2025-12-05)
        """
        dir_name, base_name = os.path.split(self.baseFilename)
        name_parts = os.path.splitext(base_name)
        base = name_parts[0]
        ext = name_parts[1] if len(name_parts) > 1 else ''
        
        date_str = archive_date.strftime('%Y-%m-%d')
        rotated_name = self.filename_pattern.format(base=base, ext=ext, date=date_str)
        
        if dir_name:
            return os.path.join(dir_name, rotated_name)
        return rotated_name

    def rotation_filename(self, default_name):
        """
        Generate filename for rotation.
        
        This method is called by the parent class. We override it to use
        our mtime-based date calculation instead of rolloverAt.
        """
        file_date = self._get_file_date()
        if file_date is None:
            file_date = self._get_today() - timedelta(days=1)
            
        return self._build_archive_filename(file_date)

    def shouldRollover(self, record):
        """
        Determine if rollover should occur.
        
        Returns True if:
        1. Current log file is from a previous day (based on mtime)
        2. Yesterday's archive already exists (another process rotated, need to reopen stream)
        """
        if self.stream is None:
            self.stream = self._open()
            
        file_date = self._get_file_date()
        if file_date is None:
            return False
            
        today = self._get_today()
        
        # Case 1: File is from a previous day
        if file_date < today:
            return True
        
        # Case 2: Yesterday's archive exists (another process already rotated)
        # This triggers "rollover" to reopen stream pointing to correct file
        yesterday = today - timedelta(days=1)
        yesterday_archive = self._build_archive_filename(yesterday)
        if os.path.exists(yesterday_archive):
            return True
        
        return False

    def doRollover(self):
        """
        Perform log rotation using optimistic locking.
        
        Strategy:
        1. Check file state and decide if rotation is needed
        2. Attempt atomic rename
        3. If rename fails (FileNotFoundError), check if another process did it
        4. Always ensure stream is reopened correctly
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        file_date = self._get_file_date()
        today = self._get_today()
        
        # If file doesn't exist or is already from today, just reopen stream
        if file_date is None or file_date >= today:
            self._update_rollover_time()
            if not self.delay:
                self.stream = self._open()
            return

        # Calculate archive filename based on file's mtime
        dfn = self._build_archive_filename(file_date)

        # Check if archive already exists
        if os.path.exists(dfn):
            if os.path.getsize(dfn) > 0:
                # Archive exists with content - another process already did it
                # Just reopen stream and continue
                pass
            else:
                # Empty archive file (abnormal) - try to remove it
                try:
                    os.remove(dfn)
                except OSError:
                    pass
        
        # Attempt rotation if archive doesn't exist (or was empty and removed)
        if not os.path.exists(dfn) and os.path.exists(self.baseFilename):
            try:
                os.rename(self.baseFilename, dfn)
            except FileNotFoundError:
                # Another process renamed the file first
                # Check if archive now exists (confirms another process did it)
                if os.path.exists(dfn):
                    # Good - another process completed rotation
                    pass
                else:
                    # File genuinely missing - unusual but not fatal
                    pass
            except OSError:
                # Other errors (permissions, disk full, etc.)
                pass

        # Delete old backups
        if self.backupCount > 0:
            self._delete_old_backups()

        # Update rollover time
        self._update_rollover_time()

        # Reopen stream (pointing to new/current debug.log)
        if not self.delay:
            self.stream = self._open()

    def _update_rollover_time(self):
        """Update rolloverAt to next rollover time."""
        current_time = int(time.time())
        self.rolloverAt = self.computeRollover(current_time)

    def _delete_old_backups(self):
        """Keep only the most recent backupCount files."""
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
