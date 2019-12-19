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
	twine upload ./dist/* --skip-existing

bundle_upload:
	python waltz push --course f19_cisc108 --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "quizzes/$(Q)Quiz $(NAME)"
	python waltz push --course f19_cisc108 --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "pages/$(S)Slides $(NAME)"
	python waltz build --course f19_cisc108 --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "Lesson $(NAME).yaml"
	python waltz push --course f19_cisc108 --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "pages/$(L)Lesson $(NAME)"

push:
	python waltz push --course f19_cisc108 --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "$(ID)"

pull:
	python waltz pull --course f19_cisc108 --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "$(ID)"

pull_honors:
	python waltz pull --course f19_cisc108_honors --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "$(ID)"

push_honors:
	python waltz push --course f19_cisc108_honors --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "$(ID)"

honors_bundle_upload:
	python waltz push --course f19_cisc108_honors --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "quizzes/$(Q)Quiz $(NAME)"
	python waltz push --course f19_cisc108_honors --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "pages/$(S)Slides $(NAME)"
	python waltz build --course f19_cisc108_honors --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "Lesson $(NAME).yaml"
	python waltz push --course f19_cisc108_honors --settings settings/ud.yaml -d C:/Users/acbart/Projects/cisc108/cisc108-python-f19-bart/ -x -i "pages/$(L)Lesson $(NAME)"