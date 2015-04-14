#!/usr/bin/env python3
#coding: utf_8

from myRecords import HeaderError
import io,sys

class gffLine(object):

    def __init__(self,line, my_line='', header=False):
        '''Object which serializes a GFF line.
		Parameters:
				- _line: the original line
				- _fields: the splitted line
				- chrom: the chromosome
				- source: source field, where the data originated from.
				- feature: mRNA, gene, exon, start/stop_codon, etc.
				- start: start of the feature
				- end: stop of the feature
				- strand: strand of the feature
				- score
				- phase
				- attributes - a dictionary which contains the extra information.
				
				Typical fields in attributes are: ID/Parent, Name'''

        self.id=None
        self.parent=None


        if line=='' and my_line!="":
            self._line=my_line
        else:
            self._line=line
        self._fields=line.rstrip().split('\t')
        self.header=header
        # if len(self._fields)!=9:
        #     print(*self._line, file=sys.stderr)

        if self.header or len(self._fields)!=9 or self._line=='':
            self.attributes={}
            self.feature=None
            
            return

        if len(self._fields)!=9: return None
        self.chrom,self.source,self.feature=self._fields[0:3]
        self.start,self.end=tuple(int(i) for i in self._fields[3:5])

        if self._fields[5]=='.': self.score=None
        else: self.score=float(self._fields[5])

        self.strand=self._fields[6]
        if self.strand=='.': self.strand=None
        assert self.strand in (None,'+','-','?')

        if self._fields[7]=='.': self.phase=None
        else: 
            try: 
                self.phase=int(self._fields[7]); assert self.phase in (0,1,2)
            except: raise

        self._Attr=self._fields[8]
        self.attributes={}

        self.attributeOrder=[]

        for item in [x for x in self._Attr.rstrip().split(';') if x!='']:
            itemized=item.split('=')
            try:
                self.attributes[itemized[0]]=itemized[1]
                self.attributeOrder.append(itemized[0])
            except IndexError:
                pass
#                raise IndexError(item, itemized, self._Attr)

        if "ID" in self.attributes or "Parent" in self.attributes or "PARENT" in self.attributes:
            tags=['Name','ID','Parent']
            if 'ID' in self.attributes:
                self.id=self.attributes['ID']
            elif "rank" in self.attributes:
                self.id=None
                if "ID" in self.attributes: del self.attributes['ID']
            elif "Name" in self.attributes:
                self.id=self.attributes['Name']
            elif "NAME" in self.attributes:
                self.id=self.attributes['NAME']
            # else:
            #     self.id=self.attributes['Parent']

        for tag in self.attributes:
            #self.__dict__[tag.lower()]=self.attributes[tag]
            if tag in self.attributes: self.__dict__[tag.lower()]=self.attributes[tag]
        if "PARENT" in self.attributes and "Parent" not in self.attributes:
            self.attributes['Parent']=self.attributes['PARENT'][:]
            del self.attributes['PARENT']
            self.parent=self.attributes['Parent']

    def __str__(self): 
        if not self.feature: return self._line.rstrip()

        if "score" in self.__dict__ and self.score: score=str(self.score)
        else: score="."
        if 'strand' not in self.__dict__ or not self.strand: strand="."
        else: strand=self.strand
        if self.phase!=None: phase=str(self.phase)
        else: phase="."
        if self.id is not None and "rank" not in self.attributes:
            attrs=["ID={0}".format(self.id)]
        else:
            attrs=[]
        if self.parent is not None:
            attrs.append("Parent={0}".format(self.attributes['Parent']))
        for att in self.attributeOrder:
            if att in ["ID","Parent"]: continue
            try: attrs.append("{0}={1}".format(att, self.attributes[att]))
            except: continue #Hack for those times when we modify the attributes at runtime
            
        line='\t'.join(
            [self.chrom, self.source,
             self.feature, str(self.start), str(self.end),
             str(score), strand, phase,
             ";".join(attrs)]
        )
        return line

    def __len__(self):
        if "end" in self.__dict__:
            return self.end-self.start+1
        else: return 0


class GFF3(object):
    def __init__(self,handle):
        if isinstance(handle,io.IOBase):
            self._handle=handle

        else:
            assert isinstance(handle,str)
            try: self._handle=open(handle)
            except: raise ValueError('File not found: {0}'.format(handle))

        self.header=False

    def __iter__(self): return self

    def __next__(self):
        line=self._handle.readline()
        if line=='': raise StopIteration

        if line[0]=="#":
            return gffLine(line, header=True)
        # while line[0]=='#':
        #     self.header+=line
        #     line=self._handle.readline()
        #     if len(line)==0: raise StopIteration
        #     if line=='': raise StopIteration
#        gff_line=gffLine(line)
#        print(line, gff_line, file=sys.stderr)

        return gffLine(line)
