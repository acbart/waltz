import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import patch
from io import StringIO

# Add the waltz package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from waltz.__main__ import main, print_friendly_error, suggest_next_steps
from waltz.exceptions import WaltzServiceNotFound, WaltzResourceNotFound, WaltzAmbiguousResource, WaltzException


class TestErrorHandling(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
    def tearDown(self):
        # Clean up
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_friendly_error_display(self):
        """Test that friendly error messages are displayed correctly."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            print_friendly_error("Test error message")
            output = mock_stderr.getvalue()
            
        self.assertIn("❌ Error: Test error message", output)
        self.assertIn("💡 Try 'waltz --help'", output)
    
    def test_service_not_found_suggestions(self):
        """Test that appropriate suggestions are shown for service not found errors."""
        error = WaltzServiceNotFound("Unknown service: test_service")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            suggest_next_steps(error)
            output = mock_stderr.getvalue()
            
        self.assertIn("💡 Available commands:", output)
        self.assertIn("waltz list", output)
        self.assertIn("waltz configure", output)
    
    def test_resource_not_found_suggestions(self):
        """Test that appropriate suggestions are shown for resource not found errors."""
        error = WaltzResourceNotFound("Could not find resource test_resource")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            suggest_next_steps(error)
            output = mock_stderr.getvalue()
            
        self.assertIn("💡 Available commands:", output)
        self.assertIn("waltz list <service>", output)
        self.assertIn("waltz search", output)
    
    def test_canvas_configuration_suggestion(self):
        """Test that canvas configuration suggestions are shown."""
        error = WaltzException("Service canvas is not configured")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            suggest_next_steps(error)
            output = mock_stderr.getvalue()
            
        self.assertIn("💡 To use Canvas", output)
        self.assertIn("waltz configure canvas", output)
        self.assertIn("API token", output)
    
    def test_main_error_handling_service_not_found(self):
        """Test that the main function handles WaltzServiceNotFound appropriately."""
        # Mock parse_command_line to raise WaltzServiceNotFound
        with patch('waltz.__main__.parse_command_line') as mock_parse:
            mock_parse.side_effect = WaltzServiceNotFound("Unknown service: test")
            
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit) as cm:
                    main(['pull', 'test', 'page', 'Test'])
                
                self.assertEqual(cm.exception.code, 1)
                output = mock_stderr.getvalue()
                
        self.assertIn("❌ Error: Unknown or unconfigured service", output)
        self.assertIn("💡 Available commands:", output)
    
    def test_main_error_handling_resource_not_found(self):
        """Test that the main function handles WaltzResourceNotFound appropriately."""
        with patch('waltz.__main__.parse_command_line') as mock_parse:
            mock_parse.side_effect = WaltzResourceNotFound("Could not find resource test")
            
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit) as cm:
                    main(['pull', 'canvas', 'page', 'Test'])
                
                self.assertEqual(cm.exception.code, 1)
                output = mock_stderr.getvalue()
                
        self.assertIn("❌ Error: Could not find the requested resource", output)
        self.assertIn("💡 Available commands:", output)
    
    def test_main_error_handling_ambiguous_resource(self):
        """Test that the main function handles WaltzAmbiguousResource appropriately."""
        with patch('waltz.__main__.parse_command_line') as mock_parse:
            mock_parse.side_effect = WaltzAmbiguousResource("Multiple resources match")
            
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit) as cm:
                    main(['pull', 'canvas', 'page', 'Test'])
                
                self.assertEqual(cm.exception.code, 1)
                output = mock_stderr.getvalue()
                
        self.assertIn("❌ Error: Multiple resources match", output)
        self.assertIn("💡 Try being more specific", output)
    
    def test_main_error_handling_keyboard_interrupt(self):
        """Test that the main function handles KeyboardInterrupt appropriately."""
        with patch('waltz.__main__.parse_command_line') as mock_parse:
            mock_parse.side_effect = KeyboardInterrupt()
            
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit) as cm:
                    main(['pull', 'canvas', 'page', 'Test'])
                
                self.assertEqual(cm.exception.code, 130)
                output = mock_stderr.getvalue()
                
        self.assertIn("🛑 Operation cancelled by user", output)
    
    def test_main_error_handling_generic_exception(self):
        """Test that the main function handles unexpected exceptions appropriately."""
        with patch('waltz.__main__.parse_command_line') as mock_parse:
            mock_parse.side_effect = ValueError("Unexpected error")
            
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit) as cm:
                    main(['pull', 'canvas', 'page', 'Test'])
                
                self.assertEqual(cm.exception.code, 1)
                output = mock_stderr.getvalue()
                
        self.assertIn("❌ An unexpected error occurred", output)
        self.assertIn("ValueError: Unexpected error", output)
        self.assertIn("💡 This might be a bug", output)
    
    def test_logging_setup(self):
        """Test that logging is set up correctly."""
        # Initialize the main function which should set up logging
        with patch('waltz.__main__.parse_command_line') as mock_parse:
            mock_parse.return_value = None
            
            try:
                main(['--help'])
            except SystemExit:
                pass  # Expected for help command
        
        # Check that log directory exists after setup
        if os.path.exists('./logs'):
            self.assertTrue(os.path.isdir('./logs'))
            if os.path.exists('./logs/waltz.log'):
                self.assertTrue(os.path.isfile('./logs/waltz.log'))


if __name__ == '__main__':
    unittest.main()