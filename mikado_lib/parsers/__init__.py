#!/usr/bin/env python3
#coding: utf_8

"""
    This module defines the iterators that will parse BED12, GTF, GFF files.
"""

import io,os
import importlib

class HeaderError(Exception):
    pass

class SizeError(Exception):
    def __init__(self,value=None): self.value=value
    def __str__(self): return str(self.value)

class Parser(object):
    '''Generic parser iterator. Base parser class.'''
    def __init__(self,handle):
        if not isinstance(handle,io.IOBase):
            try: handle=open(handle)
            except: raise TypeError
        self._handle=handle
        self.closed = False

    def __iter__(self): return self
    
    def __enter__(self):
        if self.closed is True:
            raise ValueError('I/O operation on closed file.')
        return self
    
    def __exit__(self,*args):
        self._handle.close()
        self.closed=True

    def close(self):
        self.__exit__()

    @property
    def name(self):
        return self._handle.name

    @property
    def closed(self):
        return self.__closed
    
    @closed.setter
    def closed(self,*args):
        if type(args[0]) is not bool:
            raise TypeError("Invalid value: {0}".format(args[0]))
        
        self.__closed = args[0]

class tabParser(object):
    '''Base class for iterating over tabular file formats.'''
    def __init__(self,line: str):
        if not isinstance(line,str): raise TypeError
        if line=='': raise StopIteration

        self.line=line.rstrip()
        self._fields=self.line.split('\t')

    def __str__(self): return self.line

# import mikado_lib.parsers.bed12
# import mikado_lib.parsers.GFF
# import mikado_lib.parsers.GTF