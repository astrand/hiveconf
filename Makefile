
.PHONY: dist default all install rpm

default: all

all: 
	./setup.py build

install: 
	./setup.py install
	./create_pth.sh

rpm: 
	./setup.py bdist_rpm

dist:
	./setup.py sdist