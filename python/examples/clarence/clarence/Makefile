
prgname			= clarence
PREFIX			= /usr/local
VERSION			= 0.2.2
TAR_EXCLUDE		= --exclude *.o

all:
	@echo "make install"

clean:
	rm -fr *~ *.asc

install:
	cp ./$(prgname).py $(PREFIX)/bin
	cp ./$(prgname).1 $(PREFIX)/man/man1
	cp ./clarence.hconf $(PREFIX)/etc

md5:
	@md5sum * > md5sums.asc

dist:
	@cd ..;\
	tar -cvz $(TAR_EXCLUDE) -f $(prgname)-$(VERSION).tar.gz $(prgname)-$(VERSION);\
	mv $(prgname)-$(VERSION).tar.gz $(prgname)-$(VERSION)

zip:
	@cd ..;\
	zip -r $(prgname)-$(VERSION).zip $(prgname)-$(VERSION);\
	mv $(prgname)-$(VERSION).zip $(prgname)-$(VERSION)

