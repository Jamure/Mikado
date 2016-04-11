# coding: utf-8

"""
Pretty basic class that defines a reference gene with its transcripts.
Minimal checks.
"""

import logging
import operator
from .transcript import Transcript
from ..exceptions import InvalidTranscript, InvalidCDS
from ..parsers.GFF import GffLine
from ..parsers.GTF import GtfLine
from ..utilities.log_utils import create_null_logger
from sys import intern


class Gene:

    """
    :param transcr: a transcript used to initialize the container.
    :param gid:Id of the gene.
    :param logger: an optional Logger from the logging module.
    """

    __name__ = "gene"

    def __init__(self, transcr: [None, Transcript], gid=None, logger=None, only_coding=False):

        self.transcripts = dict()
        self.__logger = None
        self.__introns = None
        self.exception_message = ''
        self.chrom, self.source, self.start, self.end, self.strand = [None] * 5
        self.only_coding = only_coding
        self.coding_transcripts = set()
        self.id = None

        if transcr is not None:
            if isinstance(transcr, Transcript):
                self.transcripts[transcr.id] = transcr
                self.id = transcr.parent[0]
                self.transcripts[transcr.id] = transcr
            elif isinstance(transcr, GffLine):
                assert transcr.is_gene is True
                self.id = transcr.id
            elif isinstance(transcr, GtfLine):
                self.id = transcr.gene

            self.chrom, self.source, self.start, self.end, self.strand = (transcr.chrom,
                                                                          transcr.source,
                                                                          transcr.start,
                                                                          transcr.end,
                                                                          transcr.strand)

        if gid is not None:
            self.id = gid
        # Internalize in memory for less memory usage
        [intern(_) for _ in [self.chrom, self.source, self.id]
         if _ is not None]

        self.logger = logger

    @property
    def logger(self):

        """
        Logger instance for the class.
        :rtype : logging.Logger
        """
        return self.__logger

    @logger.setter
    def logger(self, logger):
        """Set a logger for the instance.
        :param logger
        :type logger: logging.Logger | Nonell
        """
        if isinstance(logger, logging.Logger):
            self.__logger = logger
        elif logger is None:
            name = "gene_{0}".format(self.id if self.id else "generic")
            self.__logger = create_null_logger(name)
        else:
            raise TypeError("Invalid object for logger: {0}, (type {1})".format(
                logger, type(logger)))

        for tid in self.transcripts:
            self.transcripts[tid].logger = logger

    def add(self, transcr: Transcript):
        """
        This method adds a transcript to the storage.
        :param transcr: the transcript to be added.
        """

        self.start = min(self.start, transcr.start)
        self.end = max(self.end, transcr.end)
        self.transcripts[transcr.id] = transcr
        if transcr.strand != self.strand:
            if self.strand is None:
                self.strand = transcr.strand
            elif transcr.strand is None:
                transcr.strand = self.strand
            else:
                raise AssertionError("Discrepant strands for gene {0} and transcript {1}".format(
                    self.id, transcr.id
                ))
        transcr.logger = self.logger

    def __getitem__(self, tid: str) -> Transcript:
        return self.transcripts[tid]

    def finalize(self, exclude_utr=False):
        """
        This method will finalize the container by checking the consistency of all the
        transcripts and eventually removing incorrect ones.

        :param exclude_utr: boolean flag
        :return:
        """

        to_remove = set()
        for tid in self.transcripts:
            try:
                self.transcripts[tid].finalize()
                if self.only_coding is True and self.transcripts[tid].selected_cds_length == 0:
                    to_remove.add(tid)
                if self.transcripts[tid].selected_cds_length > 0:
                    self.coding_transcripts.add(tid)
                if exclude_utr is True:
                    self.transcripts[tid].remove_utrs()
            except InvalidCDS:
                self.transcripts[tid].strip_cds()
            except InvalidTranscript as err:
                self.exception_message += "{0}\n".format(err)
                to_remove.add(tid)
            except Exception as err:
                print(err)
                raise
        for k in to_remove:
            del self.transcripts[k]

        if len(self.transcripts) > 0:
            __new_start = min(_.start for _ in self)

            if __new_start != self.start:
                self.logger.warning("Resetting the start for %s from %d to %d",
                                    self.id, self.start, __new_start)
                self.start = __new_start

            __new_end = max(_.end for _ in self)
            if __new_end != self.end:
                self.logger.warning("Resetting the end for %s from %d to %d",
                                    self.id, self.end, __new_end)
                self.end = __new_end

    def as_dict(self):

        """
        Method to transform the gene object into a JSON-friendly representation.
        :return:
        """

        state = dict()
        for key in ["chrom", "source", "start", "end", "strand", "id"]:
            state[key] = getattr(self, key)

        state["transcripts"] = dict.fromkeys(self.transcripts.keys())

        for tid in state["transcripts"]:
            state["transcripts"][tid] = self.transcripts[tid].as_dict()

        return state

    def load_dict(self, state, exclude_utr=False, protein_coding=False):

        for key in ["chrom", "source", "start", "end", "strand", "id"]:
            setattr(self, key, state[key])

        for tid, tvalues in state["transcripts"].items():
            transcript = Transcript()
            transcript.load_dict(tvalues)
            transcript.finalize()
            if protein_coding is True and transcript.is_coding is False:
                self.logger.debug("{0} is non coding ({1}, {2})".format(
                    transcript.id,
                    transcript.combined_cds,
                    transcript.segments))
                continue
            if exclude_utr is True:
                has_utrs = (transcript.utr_length > 0)
                transcript.remove_utrs()
                if has_utrs is True and (transcript.utr_length > 0):
                    raise AssertionError("Failed to remove the UTRs!")
            self.transcripts[tid] = transcript

        self.chrom = intern(self.chrom)
        self.source = intern(self.source)
        self.id = intern(self.id)

        return

    def remove(self, tid: str):
        """

        :param tid: name of the transcript to remove.

        This method will remove a transcript from the container, and recalculate the
         necessary instance attributes.

        """

        del self.transcripts[tid]
        if len(self.transcripts) == 0:
            self.end = None
            self.start = None
            self.chrom = None
        self.start = min(self.transcripts[tid].start for tid in self.transcripts)
        self.end = max(self.transcripts[tid].end for tid in self.transcripts)

    def __repr__(self):
        return " ".join(self.transcripts.keys())

    def __str__(self):
        return self.format("gff3")

    def __iter__(self) -> Transcript:
        """Iterate over the transcripts attached to the gene."""
        return iter(self.transcripts.values())

    def __len__(self) -> int:
        return len(self.transcripts)

    def __getstate__(self):
        state = self.__dict__
        state["logger"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.logger = None

    def __lt__(self, other):
        if self.chrom != other.chrom:
            return self.chrom < other.chrom
        else:
            if self.start != other.start:
                return self.start < other.start
            elif self.end != other.end:
                return self.end < other.end
            else:
                if self.strand is not None and other.strand is not None:
                    return self.strand < other.strand
                elif self.strand is None and other.strand is not None:
                    return False
                elif self.strand is not None and other.strand is None:
                    return True
                else:
                    return False

    def __eq__(self, other):
        if self.chrom == other.chrom and self.start == other.start and \
                self.end == other.end and self.strand == other.strand:
            return True
        return False

    def format(self, format_name):

        if format_name not in ("gff", "gtf", "gff3"):
            raise ValueError(
                "Invalid format: {0}. Accepted formats: gff/gff3 (equivalent), gtf".format(
                    format_name))

        self.finalize()  # Necessary to sort the exons
        lines = []
        if format_name != "gtf":
            line = GffLine(None)
            for attr in ["chrom",
                         "source",
                         "start",
                         "end",
                         "strand"]:
                setattr(line, attr, getattr(self, attr))

            line.feature = "gene"
            line.id = self.id
            assert line.id is not None
            lines.append(str(line))

        for tid, transcript in sorted(self.transcripts.items(), key=operator.itemgetter(1)):
            lines.append(transcript.format(format_name))

        return "\n".join(lines)

    @property
    def monoexonic(self):
        """
        Boolean property. False if at least one transcript is multiexonic,
        True otherwise.
        :return: bool
        :rtype: bool
        """

        return any(transcript.monoexonic is False for transcript in self.transcripts.values())

    @property
    def introns(self):
        if self.__introns is None:
            self.__introns = set.union(*[_.introns for _ in self.transcripts.values()])

        return self.__introns

    @property
    def introns(self):
        """
        It returns the set of all introns in the container.
        :rtype : set
        """

        return set(self.transcripts[tid].introns for tid in self.transcripts)

    @property
    def exons(self):
        """
        It returns the set of all exons in the container.
        :rtype : set
        """
        return set.union(*[set(self.transcripts[tid].exons) for tid in self.transcripts])

    @property
    def has_monoexonic(self):
        """
        True if any of the transcripts is monoexonic.
        :rtype : bool
        """
        return any(len(self.transcripts[tid].introns) == 0 for tid in self.transcripts.keys())

    @property
    def monoexonic(self):
        return all(len(self.transcripts[tid].introns) == 0 for tid in self.transcripts.keys())

    @property
    def num_transcripts(self):
        """
        Number of transcripts.
        :rtype : int
        """
        return len(self.transcripts)

    @property
    def is_coding(self):
        """
        Property. It evaluates to True if at least one transcript is coding, False otherwise.
        """
        return any(self.transcripts[tid].selected_cds_length > 0 for tid in self.transcripts.keys())
