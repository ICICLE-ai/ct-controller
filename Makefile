VER=`sed -n 's/^VERSION = "\([^"]*\)".*/\1/p' ctcontroller/__init__.py`

whl:
	python -m build --wheel
sdist:
	python -m build
image: whl
	docker build --build-arg VER=$(VER) --tag tapis/ctcontroller:$(VER) .
push: image
	docker push tapis/ctcontroller:$(VER)
