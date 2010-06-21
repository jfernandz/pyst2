CDUP=../..
PKG=asterisk
PY=agi.py  agitb.py  config.py  __init__.py  manager.py
SRC=Makefile MANIFEST.in setup.py README README.html \
    $(PY:%.py=$(PKG)/%.py)

VERSIONPY=asterisk/Version.py
VERSION=$(VERSIONPY)
LASTRELEASE:=$(shell ../svntools/lastrelease -n)

USERNAME=schlatterbeck
PROJECT=pyst
PACKAGE=${PKG}
CHANGES=changes
NOTES=notes

all: $(VERSION)

$(VERSION): $(SRC)

dist: all
	python setup.py sdist --formats=gztar,zip

clean:
	rm -f MANIFEST README.html default.css \
	    $(PKG)/Version.py $(PKG)/Version.pyc ${CHANGES} ${NOTES}
	rm -rf dist build

release: upload upload_homepage announce_pypi announce

include ../make/Makefile-sf
