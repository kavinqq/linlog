"""
Tests for context module

Focus on thread-safety and real multi-threaded scenarios.
"""

import unittest
import threading
import time
from linlog.context import set_request_id, get_request_id, clear_request_id


class TestContext(unittest.TestCase):
    """Test context management with real threading scenarios"""

    def setUp(self):
        """Ensure clean state before each test"""
        clear_request_id()

    def tearDown(self):
        """Clean up after each test"""
        clear_request_id()

    def test_set_and_get_request_id(self):
        """Test basic set and get functionality"""
        test_id = 'test-uuid-123'
        set_request_id(test_id)

        self.assertEqual(get_request_id(), test_id)

    def test_get_request_id_when_not_set(self):
        """Test get returns None when not set"""
        self.assertIsNone(get_request_id())

    def test_clear_request_id(self):
        """Test clearing request ID"""
        set_request_id('test-uuid')
        clear_request_id()

        self.assertIsNone(get_request_id())

    def test_thread_isolation(self):
        """Test each thread has isolated context (simulates uwsgi multi-thread)"""
        results = {}
        errors = []

        def worker(thread_id, request_id):
            """Simulate a request handler in a thread"""
            try:
                # Set request ID for this thread
                set_request_id(request_id)

                # Simulate some work
                time.sleep(0.01)

                # Verify the ID is still correct (not contaminated by other threads)
                actual_id = get_request_id()
                results[thread_id] = actual_id

                # Verify isolation
                if actual_id != request_id:
                    errors.append(f"Thread {thread_id}: expected {request_id}, got {actual_id}")

                # Clean up
                clear_request_id()

                # Verify cleaned
                if get_request_id() is not None:
                    errors.append(f"Thread {thread_id}: failed to clear")

            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

        # Simulate 10 concurrent requests (like uwsgi threads=4)
        threads = []
        for i in range(10):
            request_id = f'request-{i}'
            t = threading.Thread(target=worker, args=(i, request_id))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 10)

        # Verify each thread had correct isolated context
        for i in range(10):
            expected = f'request-{i}'
            actual = results.get(i)
            self.assertEqual(actual, expected,
                           f"Thread {i} context leaked: expected {expected}, got {actual}")

    def test_concurrent_set_get_operations(self):
        """Test heavy concurrent operations under high load"""
        iterations = 100
        errors = []

        def hammer_context(thread_id):
            """Rapidly set/get/clear context"""
            try:
                for i in range(iterations):
                    request_id = f'thread-{thread_id}-iter-{i}'
                    set_request_id(request_id)

                    # Immediate read should match
                    actual = get_request_id()
                    if actual != request_id:
                        errors.append(
                            f"Thread {thread_id} iter {i}: set {request_id}, got {actual}"
                        )

                    clear_request_id()

                    # Should be None after clear
                    if get_request_id() is not None:
                        errors.append(f"Thread {thread_id} iter {i}: failed to clear")

            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

        # Run 5 threads hammering context
        threads = [threading.Thread(target=hammer_context, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrency errors: {errors}")

    def test_nested_thread_context(self):
        """Test parent thread context does not affect child threads"""
        parent_id = 'parent-uuid'
        child_results = {}

        def child_worker(child_id):
            """Child thread sets its own context"""
            set_request_id(f'child-{child_id}')
            time.sleep(0.01)
            child_results[child_id] = get_request_id()
            clear_request_id()

        # Parent thread sets context
        set_request_id(parent_id)

        # Spawn child threads
        children = [threading.Thread(target=child_worker, args=(i,)) for i in range(3)]

        for t in children:
            t.start()

        # Parent should still have its context
        self.assertEqual(get_request_id(), parent_id)

        for t in children:
            t.join()

        # Verify children had independent contexts
        for i in range(3):
            expected = f'child-{i}'
            actual = child_results[i]
            self.assertEqual(actual, expected)

        # Parent should still have original context
        self.assertEqual(get_request_id(), parent_id)

        clear_request_id()


if __name__ == '__main__':
    unittest.main()
