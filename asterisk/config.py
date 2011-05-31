#!/usr/bin/env python
# vim: set expandtab:
"""
Parse Asterisk configuration files.

This module provides parsing functionality for asterisk config files.

   import asterisk.config
   import sys

   # load and parse the config file
   try:
      config = asterisk.config.Config('/etc/asterisk/extensions.conf')
   except asterisk.config.ParseError, (line, reason):
      print "Parse Error line: %s: %s" % (line, reason)
      sys.exit(1)
   except IOError, reason:
      print "Error opening file: %s" % reason
      sys.exit(1)

   # print our parsed output
   for category in config.categories:
      print '[%s]' % category.name   # print the current category

      for item in category.items:
         print '   %s = %s' % (item.name, item.value)
"""

import sys

class ParseError(Exception): pass

class Line(object):
    def __init__(self, line, number):
        self.line = ''
        self.comment = ''
        line = line.strip()    # I guess we don't preserve indentation
	self.number = number
        parts = line.split(';')
        if len(parts) >= 2:
            self.line = parts[0].strip()
            self.comment = ';'.join(parts[1:]) #Just in case the comment contained ';'
        else:
            self.line = line

    def __str__(self):
        return self.get_line()

    def get_line(self):
        if self.comment and self.line:
            return '%s\t;%s' % (self.line, self.comment)
        elif self.comment and not self.line:
            return ';%s' % self.comment
        return self.line


class Category(Line):
    def __init__(self, line='', num=-1, name=None):
        Line.__init__(self, line, num)
        if self.line:
            if (self.line[0] != '[' or self.line[-1] != ']'):
                raise ParseError(self.number,  "Missing '[' or ']' in category definition")
            self.name = self.line[1:-1]
        elif name:
            self.name = name
        else:
            raise Exception("Must provide name or line representing a category")

        self.items = []
        self.comments = []

    def get_line(self):
        if self.comment:
            return '[%s]\t;%s' % (self.name, self.comment)
        return '[%s]' % self.name

    def append(self, item):
        self.items.append(item)

    def insert(self, index, item):
        self.items.insert(index, item)

    def pop(self, index=-1):
        self.items.pop(index)

    def remove(self, item):
        self.items.remove(item)


class Item(Line):
    def __init__(self, line='', num=-1, name=None, value=None):
        Line.__init__(self, line, num)
        self.style = ''
        if self.line:
            self.parse()
        elif (name and value):
            self.name = name
            self.value = value
        else:
            raise Exception("Must provide name or value representing an item")

    def parse(self):
        try:
            name, value = self.line.split('=', 1)
        except ValueError:
            if self.line.strip()[-1] == ']':
                raise ParseError(self.number, "Category name missing '['")
            else:
                raise ParseError(self.number, "Item must be in name = value pairs")

        if value and value[0] == '>':
            self.style = '>' #preserve the style of the original
            value = value[1:].strip()
        self.name = name.strip()
        self.value = value

    def get_line(self):
        if self.comment:
            return '%s =%s %s\t;%s' % (self.name, self.style, self.value, self.comment)
        return '%s =%s %s' % (self.name, self.style, self.value)

class Config(object):
    def __init__(self, filename):
        self.filename = filename
        self.raw_lines = []     # Holds the raw strings
        self.lines = []         # Holds things in order
        self.categories = []

        # load and parse the file
	self.load()
	self.parse()

    def load(self):
        self.raw_lines = open(self.filename).readlines()
        #try:
            #self.raw_lines = open(self.filename).readlines()
        #except IOError:
            #sys.stderr.write('WARNING: error opening filename: %s  No data read. Starting new file?' % self.filename)
            #self.raw_lines = []

    def parse(self):
        cat = None
	num = 0
        for line in self.raw_lines:
            num += 1
            line = line.strip()
            if not line or line[0] == ';':
                item = Line(line or '', num)
                self.lines.append(item)
                if cat: cat.comments.append(item)
                continue
            elif line[0] == '[':
                cat = Category(line, num)
                self.lines.append(cat)
                self.categories.append(cat)
                continue
            else:
                item = Item(line, num)
                self.lines.append(item)
                if cat: cat.append(item)
                continue

