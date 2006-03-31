
.PHONY: dist default all install rpm

default: all

all: 
	./setup.py build

install: 
	./setup.py install
	./create_pth.sh

rpm: 
	./setup.py bdist_rpm --release=8

dist:
# We distribute a .spec file, so that it's possible to run "rpm -ta hiveconf.tgz"
	./setup.py bdist_rpm --spec-only 
	mv dist/hiveconf.spec .
	./setup.py sdist
