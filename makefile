docs:
	cd docs && make html -b coverage

tests:
	python -m unittest discover -s tests/

verbose_tests:
	python -m unittest discover -s tests/ -v
    
coverage:
	coverage run --source=. -m unittest discover -s tests/
	coverage html -i
	coverage report
	echo "HTML version available at ./htmlcov/index.html"
	CMD /C start ./htmlcov/index.html

style:
	flake8 pedal/

publish:
	python setup.py sdist bdist_wheel
	python -m twine upload ./dist/* --skip-existing
