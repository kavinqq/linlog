"""
Tests for filters module

Test real logging filter behavior with context integration.
"""

import unittest
import logging
import threading
from linlog.filters import UUIDFilter
from linlog.context import set_request_id, get_request_id, clear_request_id


class TestUUIDFilter(unittest.TestCase):
    """Test UUIDFilter in real logging scenarios"""

    def setUp(self):
        """Clean context before each test"""
        clear_request_id()

    def tearDown(self):
        """Clean up after test"""
        clear_request_id()
        # Clean up all test loggers to prevent handler accumulation
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name.startswith('test_'):
                logger = logging.getLogger(name)
                handlers = logger.handlers[:]
                for handler in handlers:
                    handler.close()
                    logger.removeHandler(handler)

    def test_filter_adds_request_id_to_record(self):
        """Test filter adds request_id attribute to log record"""
        uuid_filter = UUIDFilter()
        test_uuid = 'test-uuid-123'
        set_request_id(test_uuid)

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Filter should add request_id
        result = uuid_filter.filter(record)

        self.assertTrue(result)  # Should always return True
        self.assertTrue(hasattr(record, 'request_id'))
        self.assertEqual(record.request_id, test_uuid)

    def test_filter_without_context_sets_na(self):
        """Test filter sets 'N/A' when no context is set"""
        uuid_filter = UUIDFilter()

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        uuid_filter.filter(record)

        self.assertEqual(record.request_id, 'N/A')

    def test_filter_in_actual_logger(self):
        """Test filter works with real logging.Logger"""
        # Create logger with filter - use unique name to avoid conflicts
        logger = logging.getLogger('test_filter_logger_unique')
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Prevent propagation to root logger

        # Custom handler to capture records
        class RecordCapture(logging.Handler):
            def __init__(self):
                super().__init__()
                self.records = []

            def emit(self, record):
                self.records.append(record)

        handler = RecordCapture()
        handler.addFilter(UUIDFilter())
        logger.addHandler(handler)

        try:
            # Set UUID and log
            test_uuid = 'real-uuid-456'
            set_request_id(test_uuid)
            logger.info('Test message')

            # Verify filter worked
            self.assertEqual(len(handler.records), 1)
            record = handler.records[0]
            self.assertEqual(record.request_id, test_uuid)
        finally:
            # Clean up request_id and logger
            clear_request_id()
            logger.removeHandler(handler)
            handler.close()

    def test_filter_with_multiple_threads(self):
        """Test filter correctness in multi-threaded logging"""
        errors = []

        class ThreadRecordCapture(logging.Handler):
            """Thread-safe record capture"""
            def __init__(self):
                super().__init__()
                self.records = []
                self._records_lock = threading.Lock()  # Use different name to avoid overriding Handler.lock

            def emit(self, record):
                with self._records_lock:
                    self.records.append({
                        'thread_id': threading.get_ident(),
                        'request_id': record.request_id,
                        'message': record.getMessage()
                    })

        handler = ThreadRecordCapture()
        handler.addFilter(UUIDFilter())

        logger = logging.getLogger('test_mt_filter_unique')
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Prevent propagation to root logger
        logger.addHandler(handler)

        def worker(thread_id, expected_uuid):
            """Worker thread that logs with UUID"""
            try:
                set_request_id(expected_uuid)

                # Log multiple times
                for i in range(5):
                    logger.info(f'Thread {thread_id} message {i}')

                clear_request_id()

            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

        # Run 10 threads simultaneously
        threads = []
        for i in range(10):
            uuid = f'thread-{i}-uuid'
            t = threading.Thread(target=worker, args=(i, uuid))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify no errors
        self.assertEqual(len(errors), 0, f"Errors: {errors}")

        # Verify all 50 log records (10 threads × 5 messages)
        self.assertEqual(len(handler.records), 50)

        # Verify each record has correct UUID
        # Group by thread
        by_thread = {}
        for rec in handler.records:
            msg = rec['message']
            # Extract thread_id from message
            import re
            match = re.match(r'Thread (\d+) message', msg)
            if match:
                thread_id = int(match.group(1))
                request_id = rec['request_id']

                if thread_id not in by_thread:
                    by_thread[thread_id] = []
                by_thread[thread_id].append(request_id)

        # Verify each thread's logs all have same UUID
        for thread_id, uuids in by_thread.items():
            expected = f'thread-{thread_id}-uuid'
            unique_uuids = set(uuids)

            self.assertEqual(len(unique_uuids), 1,
                           f"Thread {thread_id} had multiple UUIDs: {unique_uuids}")
            self.assertEqual(uuids[0], expected,
                           f"Thread {thread_id}: expected {expected}, got {uuids[0]}")

        # Clean up
        logger.removeHandler(handler)


if __name__ == '__main__':
    unittest.main()
