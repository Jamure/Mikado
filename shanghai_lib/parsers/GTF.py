#coding: utf_8

import sys,os.path
import copy
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from shanghai_lib.parsers import Parser
# import re

class gtfLine(object):
    '''This class defines a typical GTF line, with some added functionality to make it useful in e.g. parsing cufflinks GTF files or creating GTF lines from scratch.
    Fields:
    - chrom
    - source
    - feature
    - start,end
    - score
    - phase
    - strand
    - info (a dictionary containing all the annotations contained in the last field)

    - gene: the gene_id
    - transcript: the transcript_id

    For cufflinks files, also:
    - nearest_ref
    - tss_id
    - ccode'''

    #_slots=['chrom','source','feature','start',\
    #'end','score','strand','phase','info']

    def __init__(self,*args):
        self.header=False
        self.attributes={}
        
        self.feature = None
        if len(args)>0:
            line=args[0]
        else:
            return
        if line=='':
            raise StopIteration
        
        if line==None or line[0]=="#" or line.rstrip()=='':
            self.fields=[]
            self.attributes = dict()
            self.transcript=None
            self.gene=None
            if line is None:
                self.header=False
            else:
                self.header = True
            return 
        else:
            assert isinstance(line,str)
            self.fields=line.rstrip().split('\t')
            if len(self.fields)!=9:
                raise ValueError(line)
            self.chrom,self.source,self.feature=self.fields[0:3]
            self.start,self.end=tuple(int(i) for i in self.fields[3:5])
            self.end=self.end
            try: self.score=float(self.fields[5])
            except ValueError:
                if self.fields[5]=='.': self.score=None
            self.strand,self.phase=self.fields[6:8]
            if self.strand in ('.','\x00'):
                self.strand=None
            assert self.strand in ('+',None,'-'), (self.strand,line)
            if self.phase=='.': self.phase=None
            else:
                try:
                    self.phase=int(self.phase)
                    assert self.phase in (0,1,2)
                except: raise

            self._info=self.fields[8].split(';')
            try: self._info.remove('')
            except ValueError: pass
            for info in self._info:
                info=info.lstrip().split(' ') #Divido l'annotazione, e rimuovo le virgolette
                try: self.attributes[info[0]]=info[1].replace('"','')
                except IndexError: raise IndexError(self._info, info)

            if 'exon_number' in self.attributes: self.attributes['exon_number']=int(self.attributes['exon_number'])
            assert 'gene_id','transcript_id' in self.attributes
#             self.attributes["ID"]=self.id
#             self.attributes["Parent"]=self.parent
#             if self.feature=="transcript":
#                 self.attributes["ID"]=self.id=self.transcript
#                 self.parent=self.attributes["Parent"]=self.gene
#             else:
#                 self.attributes["Parent"]=self.parent=self.transcript
            
            if 'nearest_ref' in self.attributes: self.nearest_ref= self.attributes['nearest_ref']
            if 'tss_id' in self.attributes: self.tss_id= self.attributes['tss_id']
#             if 'class_code' in self.info: self.ccode=self.info['class_code']
            for tag in [x for x in list(self.attributes.keys()) if x not in ('gene_id','transcript_id','nearest_ref','tss_id','class_code')]:
                self.__dict__[tag.lower()]=self.attributes[tag]
                                
          
    def __str__(self):
        '''Returns the GTF string.'''
        self.fields=[]
        if self.fields==[]: #Devo ricostruire i campi se ho inizializzato da una riga vuota
            self.fields=[self.chrom,self.source,self.feature,
                         self.start,self.end,self.score,
                         self.strand, self.phase]
            for i in range(len(self.fields)):
                if self.fields[i]==None: self.fields[i]='.' #Correggere per campi vuoti
                self.fields[i]=str(self.fields[i])
            self._info=[]
            assert 'gene_id','transcript_id' in self.attributes
            if type(self.gene) is list:
                gene=",".join(self.gene)
            else: 
                gene=self.gene
            self.attributes['gene_id']=gene
            if self.attributes['transcript_id'] is None:
                self.attributes['transcript_id']=self.transcript

            order=['gene_id','transcript_id','exon_number','gene_name','transcript_name'] #Questo è l'ordine originale dei campi nel gtf di umano

            for tag in order:
                if tag in self.attributes:
                    if type(self.attributes[tag]) is list:
                        val = ",".join(self.attributes[tag])
                    else:
                        val = self.attributes[tag]
                    self._info.append( "{0} \"{1}\"".format(tag, val ) )

            for info in filter(lambda x: x not in order, self.attributes.keys()):
                if type(self.attributes[info]) is list:
                        val = ",".join(self.attributes[info])
                else:
                    val = self.attributes[info]
                self._info.append("{0} \"{1}\"".format(info, val ) )

            self.fields.append('; '.join(self._info))
            self.fields[-1]+=';' #Fields finito, si può stampare.

        assert self.fields[0]!="", self.fields
        return '\t'.join(self.fields)

    def copy(self):
        return copy.copy(self)

    def toGFF3(self, feature_type="gene", source=None):
        '''Converts the GTF line into a GFF3 one.'''
        attributes=[]

        #Redefine source variable if asked
        if source is not None:
            self.source=source
        
        if self.feature=='gene':
            if feature_type=="match": return
            if 'gene_name' not in self.attributes: self.attributes['gene_name']=self.attributes['gene_id']
            if 'description' not in self.attributes: self.attributes['description']='NA'
            attributes=['ID='+self.attributes['gene_id'],'Name='+self.attributes['gene_name']]

        elif self.feature=='mRNA' or self.feature=="transcript":
            if feature_type=="gene":
                if 'transcript_name' not in self.attributes: self.attributes['transcript_name']=self.attributes['transcript_id']
                attributes=['ID='+self.attributes['transcript_id'],
                            'Parent='+self.attributes['gene_id'],
                            'Name='+self.attributes['transcript_name']]
            elif feature_type=="match":
                self.feature="match"
                attributes=["ID={0}".format(self.attributes["transcript_id"]),
                            "Name={0}".format(self.attributes["transcript_id"])]
                
        elif self.feature in ('exon','CDS'):

#            assert 'exon_number' in self.info
            if feature_type=="match":
                self.feature="match_part"

            if "exon_number" in self.attributes:
                attributes=['ID={0}:exon-{1}'.format(self.transcript, self.attributes["exon_number"]),
                            'Parent={0}'.format(self.attributes['transcript_id'])]
            else:
                attributes=['Parent={0}'.format(self.attributes['transcript_id'])]
            

        elif self.feature in ('UTR', 'five prime UTR', 'three prime UTR'):
            if self.feature=='UTR': raise ValueError('I cannot work with "UTR" only currently! Error in: {0}'.format(self.attributes['transcript_id'])) #I have to think about a smart way of doing this..
            if self.feature=='five prime UTR': ut='5'
            else: ut='3'
            attributes=['ID=utr.'+ut,
                        'Parent='+self.attributes['transcript_id']]

        elif self.feature in ('start_codon','stop_codon'):
            attributes=['ID='+self.feature,
                        'Parent='+self.attributes['transcript_id']]

        if self.score==None: score='.'
        else: score=str(self.score)

        if self.phase==None: phase='.'
        else: phase=str(self.phase)

        if self.strand==None: strand='.'
        else: strand=self.strand

        start=min(self.start,self.end)
        stop=max(self.start,self.end)

        line=[self.chrom,self.source,self.feature,str(start),str(stop),score,strand,phase]
        line+=[';'.join(attributes)]
        return '\t'.join(line)

    @property
    def name(self):
        return self.id
    
    @name.setter
    def name(self,*args):
        if type(args[0]) is not str:
            raise TypeError("Invalid value for name: {0}".format(args[0]))
        self.id = args[0]
        
    @property
    def is_transcript(self):
        if self.feature is None: return False
        if "transcript"==self.feature or "RNA" in self.feature:
            return True
        return False
    
    @property
    def strand(self):
        return self.__strand
    
    @strand.setter
    def strand(self,strand):
        if strand in ("+", "-"):
            self.__strand=strand
        elif strand in (None,".","?"):
            self.__strand=None
        else:
            raise ValueError("Invalid value for strand: {0}".format(strand)) 
    
    @property
    def parent(self):
        '''This property looks up the "Parent" field in the "attributes" dictionary. 
        If the line is a transcript line, it returns the gene field.
        Otherwise, it returns the transcript field.
        In order to maintain interface consistency with the GFF objects and contrary to other attributes,
        this property returns a *list*, not a string. This is due to the fact that GFF files support
        multiple inheritance by separating the parent entries with a comma.'''

        if self.is_transcript is True:
            return [self.gene]
        else:
            return [self.transcript]
    
    @parent.setter
    def parent(self,parent):
        if type(parent) is list:
            assert len(parent)==1 and type(parent[0]) is str
            parent=parent[0]
        elif type(parent) is not str:
            raise TypeError("Invalid type for GTF parent: {0}, {1}".format(parent, type(parent)))
        if self.is_transcript is True:
            self.gene=parent
        else:
            self.transcript=parent
        
    @property
    def id(self):
        if self.is_transcript is True:
            return self.transcript
        else:
            return None
    
    @id.setter
    def id(self, Id):
        if self.is_transcript is True:
            self.transcript = Id 
        else:
            pass

    @property
    def gene(self):
        return self.attributes["gene_id"]
    
    @gene.setter
    def gene(self,gene):
        self.attributes["gene_id"]=self.__gene=gene
        if self.is_transcript:
            self.attributes["Parent"]=gene

    @property
    def transcript(self):
        return self.attributes["transcript_id"]
    
    @transcript.setter
    def transcript(self,transcript):
        self.attributes["transcript_id"]=self.__transcript=transcript
        if self.is_transcript is True:
            self.attributes["ID"]=transcript
        else:
            self.attributes["Parent"]=[transcript]



    @property
    def is_parent(self):
        if self.is_transcript is True:
            return True
        return False
    
    @property
    def is_exon(self):
        if self.feature is None:
            return False
        f=self.feature.upper()
        if f in ("EXON", "CDS") or "UTR" in f or "CODON" in f:
            return True
        return False

class GTF(Parser):
    '''The parsing class.'''
    def __init__(self,handle):
        super().__init__(handle)
        
    def __next__(self):
        line=self._handle.readline()
        if line=='': raise StopIteration
        return gtfLine(line)

    
    
    