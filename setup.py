from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()
with open("requirements.txt", "r") as fh:
    install_requires = fh.read().splitlines()
with open("requirements-dev.txt", "r") as fh:
    dev_requires = fh.read().splitlines()

setup(name='lms-waltz',
      entry_points={
          'console_scripts': [
              'waltz = waltz.__main__:main'
          ]
      },
      version='0.2.5',
      description='Coordinate resources between an LMS like Canvas and a local directory',
      keywords= 'lms learning management system curriculum curricular resources',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='Austin Cory Bart',
      author_email='acbart@udel.edu',
      url='https://github.com/acbart/waltz',
      install_requires=install_requires,
      extras_require={
          'dev': dev_requires
      },
      packages=['waltz', 'waltz.tools', 'waltz.services',
                'waltz.services.blockpy', 'waltz.services.canvas', 'waltz.services.gradescope',
                'waltz.services.gradescope.pyscope',
                'waltz.services.local',
                'waltz.resources', 'waltz.resources.quizzes'],
      classifiers=[
          "Development Status :: 4 - Beta",
          "Environment :: Console",
          "Intended Audience :: Education",
          "Programming Language :: Python :: 3",
          "Topic :: Education",
          "Topic :: Text Processing :: Markup",
          "Topic :: Utilities",
          "Operating System :: OS Independent",
          "Typing :: Typed"
      ],
      python_requires='>=3.6',
      )
