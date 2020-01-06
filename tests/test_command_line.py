import os
import unittest
from unittest.mock import patch, mock_open
from pyfakefs.fake_filesystem_unittest import TestCase
import json

from waltz.command_line import parse_command_line
from waltz.exceptions import WaltzException

with open("secret_testing_data.json") as secret_testing_data_file:
    SECRET_TESTING_DATA = json.load(secret_testing_data_file)
# TODO: Improve Canvas tests to use a playback cache for requests

class TestCommandLine(TestCase):

    # Hack to allow requests to work with pyfakefs
    fixture_path = os.path.join(os.path.dirname(__file__), '../venv/lib/site-packages/certifi/cacert.pem')
    def setUp(self):
        if os.path.exists('.waltz.db'):
            os.remove('.waltz.db')
        self.setUpPyfakefs()
        self.fs.add_real_directory(self.fixture_path)

    def test_init(self):
        registry = parse_command_line(['init'])
        print(open('.waltz').read())
        #self.assertEqual(len(registry.services), 3)
        #self.assertIn('local', registry.courses)
        #self.assertEqual(registry.courses['f19_cisc108'].name, 'f19_cisc108')
        #self.assertEqual(len(registry.courses['f19_cisc108'].services), 1)
        #self.assertIn('local', registry.courses['f19_cisc108'].services)

    def test_list(self):
        registry = parse_command_line(['init'])
        parse_command_line(['list'])
        with open("Final Exam.md", 'w') as final_exam:
            final_exam.write("Some _hard_ or *easy* questions?")
        parse_command_line(['list', 'local'])

    def test_add_service(self):
        registry = parse_command_line(['init'])
        parse_command_line(['configure', 'canvas', 'ud_canvas',
                           '--base', 'https://canvas.instructure.com/',
                           '--course', '946043',
                           '--token', SECRET_TESTING_DATA['CANVAS_TOKEN_DATA']])
        parse_command_line(['list', 'canvas', 'pages'])
        parse_command_line(['download', 'canvas', 'page', 'Abstraction'])
        # > waltz download canvas page Abstraction
        # > waltz decode Abstraction
        # > waltz encode Abstraction
        # > waltz upload canvas page Abstraction
        # > waltz pull "Abstraction"
        #parse_command_line(['convert', 'page', 'Abstraction', 'markdown'])
        #self.assertEqual(len(registry.courses['f19_cisc108'].services), 2)
        #self.assertIn('local', registry.courses['f19_cisc108'].services)
        #print(registry.courses['f19_cisc108'].services['local'])

if __name__ == '__main__':
    unittest.main()
