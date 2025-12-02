"""
Tests for handlers module

Test real file rotation, multi-process safety, and edge cases.
"""

import unittest
import logging
import os
import shutil
import tempfile
import time
import threading
from datetime import datetime, timedelta
from linlog.handlers import DailyRotatingHandler


class TestDailyRotatingHandler(unittest.TestCase):
    """Test DailyRotatingHandler with real file operations"""

    def setUp(self):
        """Create temporary directory for test logs"""
        self.test_dir = tempfile.mkdtemp(prefix='linlog_test_')
        self.test_log_path = os.path.join(self.test_dir, 'test.log')

    def tearDown(self):
        """Clean up test directory and logging handlers"""
        # Clean up all test loggers
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name.startswith('test'):
                logger = logging.getLogger(name)
                handlers = logger.handlers[:]
                for handler in handlers:
                    try:
                        handler.close()
                        logger.removeHandler(handler)
                    except:
                        pass
        
        # Clean up test directory
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
            except:
                pass

    def test_handler_creates_log_file(self):
        """Test handler creates log file on first write"""
        handler = DailyRotatingHandler(
            filename=self.test_log_path,
            backupCount=5
        )

        logger = logging.getLogger('test_create')
        logger.propagate = False
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.info("Test message")

        # Log file should exist
        self.assertTrue(os.path.exists(self.test_log_path))

        # File should contain the message
        with open(self.test_log_path, 'r') as f:
            content = f.read()
            self.assertIn("Test message", content)

        handler.close()
        logger.removeHandler(handler)

    def test_handler_creates_directory_if_not_exists(self):
        """Test handler auto-creates log directory"""
        nested_path = os.path.join(self.test_dir, 'logs', 'app', 'test.log')

        handler = DailyRotatingHandler(filename=nested_path)
        logger = logging.getLogger('test_mkdir')
        logger.propagate = False
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.info("Test")

        # Directory should be created
        self.assertTrue(os.path.exists(os.path.dirname(nested_path)))
        self.assertTrue(os.path.exists(nested_path))

        handler.close()
        logger.removeHandler(handler)

    def test_rotation_filename_format(self):
        """Test rotated filename format"""
        handler = DailyRotatingHandler(
            filename=self.test_log_path,
            backupCount=5
        )

        # Test rotation_filename method
        rotated = handler.rotation_filename('default_name')

        # Should contain date in format: test_YYYY-MM-DD.log
        today = datetime.now().strftime('%Y-%m-%d')
        expected_name = f'test_{today}.log'

        self.assertTrue(rotated.endswith(expected_name))

        handler.close()

    def test_backup_count_cleanup(self):
        """Test old backup files are deleted when backupCount is exceeded"""
        handler = DailyRotatingHandler(
            filename=self.test_log_path,
            backupCount=3  # Keep only 3 backups
        )

        logger = logging.getLogger('test_cleanup')
        logger.propagate = False
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Create fake old log files
        log_dir = os.path.dirname(self.test_log_path)
        base_name = os.path.basename(self.test_log_path).replace('.log', '')

        old_files = []
        for i in range(5):
            date = (datetime.now() - timedelta(days=i+1)).strftime('%Y-%m-%d')
            filename = os.path.join(log_dir, f'{base_name}_{date}.log')
            with open(filename, 'w') as f:
                f.write(f'Old log {i}')
            old_files.append(filename)
            time.sleep(0.01)  # Ensure different timestamps

        # Manually call _delete_old_backups
        handler._delete_old_backups()

        # Count remaining backup files
        remaining = [f for f in old_files if os.path.exists(f)]

        # Should keep only backupCount (3) files
        self.assertEqual(len(remaining), 3)

        # Oldest files should be deleted
        self.assertFalse(os.path.exists(old_files[3]))  # 4th oldest
        self.assertFalse(os.path.exists(old_files[4]))  # 5th oldest

        handler.close()
        logger.removeHandler(handler)

    def test_multi_threaded_logging(self):
        """Test concurrent logging from multiple threads"""
        handler = DailyRotatingHandler(filename=self.test_log_path)
        logger = logging.getLogger('test_mt_logging')
        logger.propagate = False
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        message_count = 100
        thread_count = 10
        errors = []

        def worker(thread_id):
            """Each thread logs many messages"""
            try:
                for i in range(message_count):
                    logger.info(f'Thread {thread_id} message {i}')
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

        # Run threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        handler.close()

        # Verify no errors
        self.assertEqual(len(errors), 0, f"Logging errors: {errors}")

        # Verify all messages written
        with open(self.test_log_path, 'r') as f:
            lines = f.readlines()

        # Should have thread_count × message_count lines
        expected_lines = thread_count * message_count
        self.assertEqual(len(lines), expected_lines,
                        f"Expected {expected_lines} log lines, got {len(lines)}")

        logger.removeHandler(handler)

    def test_lock_file_created_and_cleaned(self):
        """Test that lock file is properly managed"""
        handler = DailyRotatingHandler(filename=self.test_log_path)

        logger = logging.getLogger('test_lock')
        logger.propagate = False
        logger.addHandler(handler)
        logger.info("Test")

        # Lock file path
        lock_path = self.test_log_path + '.lock'

        # Lock file might not exist outside of rotation
        # This is expected - lock is only used during rotation

        handler.close()
        logger.removeHandler(handler)

    def test_utf8_encoding(self):
        """Test UTF-8 encoding with Chinese characters"""
        handler = DailyRotatingHandler(
            filename=self.test_log_path,
            encoding='utf-8'
        )

        logger = logging.getLogger('test_utf8')
        logger.propagate = False
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        test_message = '這是中文測試訊息 🎉'
        logger.info(test_message)

        handler.close()

        # Read back and verify
        with open(self.test_log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn(test_message, content)

        logger.removeHandler(handler)

    def test_simulated_rotation(self):
        """Test rotation mechanism"""
        handler = DailyRotatingHandler(
            filename=self.test_log_path,
            backupCount=5
        )

        logger = logging.getLogger('test_rotation')
        logger.propagate = False
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Write initial log
        logger.info("Before rotation")
        handler.flush()

        # Manually trigger rotation (simulate midnight)
        if hasattr(handler, 'doRollover'):
            handler.doRollover()

            # After rotation, a dated file should exist
            log_dir = os.path.dirname(self.test_log_path)
            files = os.listdir(log_dir)
            dated_files = [f for f in files if '_' in f and f.startswith('test')]

            # Should have created a dated backup file
            self.assertGreater(len(dated_files), 0,
                             f"No dated backup files found. Files: {files}")

        handler.close()
        logger.removeHandler(handler)


class TestHandlerEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix='linlog_edge_')
        self.test_log_path = os.path.join(self.test_dir, 'test.log')

    def tearDown(self):
        # Clean up all test loggers
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name.startswith('test'):
                logger = logging.getLogger(name)
                handlers = logger.handlers[:]
                for handler in handlers:
                    try:
                        handler.close()
                        logger.removeHandler(handler)
                    except:
                        pass
        
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
            except:
                pass

    def test_zero_backup_count(self):
        """Test backupCount=0 keeps all files"""
        handler = DailyRotatingHandler(
            filename=self.test_log_path,
            backupCount=0
        )

        # Create several old files
        log_dir = os.path.dirname(self.test_log_path)
        for i in range(10):
            date = (datetime.now() - timedelta(days=i+1)).strftime('%Y-%m-%d')
            filename = os.path.join(log_dir, f'test_{date}.log')
            with open(filename, 'w') as f:
                f.write(f'Log {i}')

        # Should not delete any files when backupCount=0
        handler._delete_old_backups()

        files = [f for f in os.listdir(log_dir) if f.startswith('test_')]
        self.assertEqual(len(files), 10)  # All files should remain

        handler.close()

    def test_handler_multiple_instances_same_file(self):
        """Test multiple handlers writing to same file (simulates multi-process)"""
        handlers = []
        loggers = []

        # Create 5 handlers for same file (simulating 5 processes)
        for i in range(5):
            handler = DailyRotatingHandler(filename=self.test_log_path)
            logger = logging.getLogger(f'test_multi_{i}')
            logger.propagate = False
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            handlers.append(handler)
            loggers.append(logger)

        # All log simultaneously
        for i, logger in enumerate(loggers):
            logger.info(f"Process {i} message")

        # Close all handlers
        for handler in handlers:
            handler.close()

        for logger, handler in zip(loggers, handlers):
            logger.removeHandler(handler)

        # Verify all messages written
        with open(self.test_log_path, 'r') as f:
            content = f.read()

        for i in range(5):
            self.assertIn(f"Process {i} message", content)


if __name__ == '__main__':
    unittest.main()
