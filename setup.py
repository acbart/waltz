from distutils.core import setup

setup(name='Waltz',
      entry_points={
          'console_scripts': [
              'waltz = waltz.__main__:main'
          ]
      },
      version='0.1.0',
      description='Coordinate resources between an LMS like Canvas and a local directory',
      author='Austin Cory Bart',
      author_email='acbart@udel.edu',
      url='https://github.com/acbart/waltz',
      install_requires=[
          'tqdm',
          'requests',
          'ruamel.yaml',
          'jinja2',
          'markdown',
          'requests_cache',
          'python-dateutil',
          'html2text',
          'canvasapi'
      ],
      packages=['waltz', 'waltz.tools', 'waltz.services',
                'waltz.services.blockpy', 'waltz.services.canvas', 'waltz.services.local',
                'waltz.resources'],
      )
