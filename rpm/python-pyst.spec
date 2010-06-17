Summary: An interface to AGI
Name: python-pyst
Version: 0.0.5
Release: 2.centos4.0
Source0: http://prdownloads.sourceforge.net/pyst/pyst-%{version}.tar.gz
License: LGPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-buildroot
URL: http://sourceforge.net/projects/pyst
Requires: python
BuildRequires: python-devel 
BuildRequires: python Distutils

%description
Pyst consists of a set of interfaces and libraries to allow
programming of Asterisk from python. The library currently
supports AGI, AMI, and the parsing of Asterisk configuration
files. The library also includes debugging facilities for AGI.

%prep
%setup -q -n pyst-%{version}

%build
CFLAGS="$RPM_OPT_FLAGS" python setup.py build

%install
python setup.py install --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
mkdir -p $RPM_BUILD_ROOT/usr/share/doc/python-pyst
cp debian/copyright $RPM_BUILD_ROOT/usr/share/doc/python-pyst

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%doc /usr/share/doc/python-pyst/*
%{_libdir}/python*/site-packages/asterisk/

%changelog
* Tue Mar 21 2006 Matthew Nicholson <mnicholson@digium.com> el4.3
- Bumped version number.

* Thu Feb 23 2006 Antoine Brenner <http://www.gymglish.com> el4.2
- Fixed source0 line

* Tue Feb 9 2006 Antoine Brenner <http://www.gymglish.com> el4.1
- Initial Package

