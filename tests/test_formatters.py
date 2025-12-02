"""
Tests for formatters module

Focus on real functionality, not just coverage.
"""

import unittest
import logging
import json
from datetime import datetime
from linlog.formatters import StandardFormatter, JSONFormatter


class TestStandardFormatter(unittest.TestCase):
    """Test StandardFormatter with real scenarios"""

    def setUp(self):
        self.formatter = StandardFormatter()

    def tearDown(self):
        """Clean up loggers after each test"""
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

    def test_basic_format_without_uuid(self):
        """Test basic log format without UUID"""
        record = logging.LogRecord(
            name='test.module',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        result = self.formatter.format(record)

        # Should have: [timestamp][level][name:line]：message
        self.assertIn('[INFO]', result)
        self.assertIn('[test.module:42]', result)
        self.assertIn('：Test message', result)
        self.assertNotIn('N/A', result)  # No UUID should not show N/A

    def test_format_with_uuid(self):
        """Test log format with UUID present"""
        record = logging.LogRecord(
            name='test.module',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Request started',
            args=(),
            exc_info=None
        )
        record.request_id = 'abc-123-def-456'

        result = self.formatter.format(record)

        # Should include UUID
        self.assertIn('[abc-123-def-456]', result)
        self.assertIn('[INFO]', result)
        self.assertIn('[test.module:42]', result)
        self.assertIn('：Request started', result)

    def test_format_with_uuid_na_should_not_show(self):
        """Test that 'N/A' UUID is not displayed"""
        record = logging.LogRecord(
            name='test.module',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.request_id = 'N/A'

        result = self.formatter.format(record)

        # Should NOT show N/A in output
        self.assertNotIn('[N/A]', result)
        self.assertIn('[INFO]', result)

    def test_show_uuid_false(self):
        """Test disabling UUID display"""
        formatter = StandardFormatter(show_uuid=False)
        record = logging.LogRecord(
            name='test.module',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.request_id = 'abc-123'

        result = formatter.format(record)

        # UUID should NOT be in output even if present
        self.assertNotIn('[abc-123]', result)
        self.assertIn('[INFO]', result)

    def test_exception_formatting(self):
        """Test that exceptions are properly formatted"""
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name='test.module',
            level=logging.ERROR,
            pathname='test.py',
            lineno=42,
            msg='Error occurred',
            args=(),
            exc_info=exc_info
        )

        result = self.formatter.format(record)

        # Should contain error message and traceback
        self.assertIn('Error occurred', result)
        self.assertIn('ValueError: Test error', result)
        self.assertIn('Traceback', result)

    def test_custom_date_format(self):
        """Test custom date format"""
        formatter = StandardFormatter(datefmt='%Y%m%d_%H%M%S')
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None
        )

        result = formatter.format(record)

        # Should use custom date format (YYYYMMDD_HHMMSS)
        import re
        self.assertTrue(re.search(r'\[\d{8}_\d{6}\]', result))

    def test_chinese_colon_in_output(self):
        """Test that Chinese colon is used as separator"""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='測試訊息',
            args=(),
            exc_info=None
        )

        result = self.formatter.format(record)

        # Should use Chinese colon (：) not English (:)
        self.assertIn('：測試訊息', result)


class TestJSONFormatter(unittest.TestCase):
    """Test JSONFormatter with real scenarios"""

    def setUp(self):
        self.formatter = JSONFormatter()

    def tearDown(self):
        """Clean up loggers after each test"""
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

    def test_basic_json_format(self):
        """Test basic JSON output structure"""
        record = logging.LogRecord(
            name='test.module',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.module = 'test'
        record.funcName = 'test_func'

        result = self.formatter.format(record)

        # Should be valid JSON
        data = json.loads(result)

        self.assertEqual(data['level'], 'INFO')
        self.assertEqual(data['logger'], 'test.module')
        self.assertEqual(data['line'], 42)
        self.assertEqual(data['message'], 'Test message')
        self.assertEqual(data['module'], 'test')
        self.assertEqual(data['function'], 'test_func')
        self.assertIn('timestamp', data)

    def test_json_with_request_id(self):
        """Test JSON output includes request_id"""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None
        )
        record.module = 'test'
        record.funcName = 'test_func'
        record.request_id = 'test-uuid-123'

        result = self.formatter.format(record)
        data = json.loads(result)

        self.assertEqual(data['request_id'], 'test-uuid-123')

    def test_json_with_exception(self):
        """Test JSON output includes exception info"""
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name='test',
            level=logging.ERROR,
            pathname='test.py',
            lineno=1,
            msg='Error',
            args=(),
            exc_info=exc_info
        )
        record.module = 'test'
        record.funcName = 'test_func'

        result = self.formatter.format(record)
        data = json.loads(result)

        self.assertIn('exception', data)
        self.assertIn('ValueError: Test error', data['exception'])

    def test_json_chinese_characters(self):
        """Test JSON properly handles Chinese characters"""
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='中文測試訊息',
            args=(),
            exc_info=None
        )
        record.module = 'test'
        record.funcName = 'test_func'

        result = self.formatter.format(record)
        data = json.loads(result)

        # Should preserve Chinese characters (not escaped)
        self.assertEqual(data['message'], '中文測試訊息')
        self.assertIn('中文', result)  # Should be in raw output


if __name__ == '__main__':
    unittest.main()
