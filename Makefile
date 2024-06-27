VER=`cat VERSION.txt`

whl:
	python setup.py bdist_wheel
sdist:
	python setup.py sdist
image: whl
	docker build --build-arg VER=$(VER) --tag tapis/ctcontroller:$(VER) .
push: image
	docker push tapis/ctcontroller:$(VER)
