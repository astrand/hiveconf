
.PHONY: dist default all install rpm

default: all

all: 
	./setup.py build

install: 
	./setup.py install
	./create_pth.sh

rpm: dist
	mv hiveconf.spec hiveconf.tmp
	echo '%define _binary_payload w9.gzdio' > hiveconf.spec
	echo '%define _binary_filedigest_algorithm 1' >> hiveconf.spec
	echo '%define _noPayloadPrefix 1' >> hiveconf.spec
	cat hiveconf.tmp >> hiveconf.spec
	rm hiveconf.tmp
	rpmbuild -ba hiveconf.spec --nodirtokens

dist: 
# We distribute a .spec file, so that it's possible to run "rpm -ta hiveconf.tgz"
	rm -rf dist
	./setup.py bdist_rpm --spec-only --release=1
	cp dist/hiveconf.spec .
	./setup.py sdist
