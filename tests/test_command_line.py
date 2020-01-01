import unittest
from unittest.mock import patch, mock_open
from pyfakefs.fake_filesystem_unittest import TestCase

from waltz.command_line import parse_command_line


class TestCommandLine(TestCase):
    def setUp(self):
        self.setUpPyfakefs()

    def test_add_course(self):
        registry = parse_command_line(['add', 'f19_cisc108', 'f19_cisc108'])
        #print(open('settings/registry.yaml').read())
        self.assertEqual(len(registry.courses), 1)
        self.assertIn('f19_cisc108', registry.courses)
        self.assertEqual(registry.courses['f19_cisc108'].name, 'f19_cisc108')
        self.assertEqual(len(registry.courses['f19_cisc108'].services), 1)
        self.assertIn('local', registry.courses['f19_cisc108'].services)

    def test_show_courses(self):
        parse_command_line(['add', 'f19_cisc108', 'f19_cisc108'])
        # print(open('settings/registry.yaml').read())
        registry = parse_command_line(['list', 'courses'])
        #self.assertEqual(True, False)

    def test_add_service(self):
        parse_command_line(['add', 'f19_cisc108', 'f19_cisc108'])
        registry = parse_command_line(['copy', 'canvas', 'ud_canvas', '--base', 'https://udel.instructure.com/'])
        self.assertEqual(len(registry.courses['f19_cisc108'].services), 2)
        self.assertIn('local', registry.courses['f19_cisc108'].services)
        print(registry.courses['f19_cisc108'].services['local'])
        print(open('settings/registry.yaml').read())

if __name__ == '__main__':
    unittest.main()
