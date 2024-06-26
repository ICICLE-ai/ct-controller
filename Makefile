VER=0.1

whl:
	python setup.py bdist_wheel
sdist:
	python setup.py sdist
image: whl
	docker build --tag tapis/ctcontroller:$(VER) .
