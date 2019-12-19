import argparse
import waltz.sync

parser = argparse.ArgumentParser(description='Sync resources')
parser.add_argument('verb', choices=['pull', 'push', 'build', 'publicize'])
parser.add_argument('--course', '-c', help='The specific course to perform operations on. Should be a valid course '
                                           'label, not the ID')
parser.add_argument('--settings', '-s', help='The settings file to use. Defaults to "settings.yaml". If the file does '
                                             'not exist, it will be created.', default='settings/settings.yaml')
parser.add_argument('--id', '-i', help='The specific resource ID to manipulate. If not specified, all resources are '
                                       'used', default=None)
parser.add_argument('--destination', '-d', help='Where course files will be downloaded to', default=None)
parser.add_argument('--format', '-f', help='What format to generate the result into.',
                    choices=['html', 'json', 'raw', 'pdf', 'text', 'yaml'], default='raw')
parser.add_argument('--ignore', '-x', help='Ignores any cached files in processing the quiz results',
                    action='store_true', default=False)
parser.add_argument('--quiet', '-q', help='Silences the output', action='store_true', default=False)
args = parser.parse_args()

waltz.sync.main(args)
