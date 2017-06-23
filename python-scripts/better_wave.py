"""Stuff to parse WAVE files.

Usage.

Writing WAVE files:
      f = wave.open(file, 'w')
where file is either the name of a file or an open file pointer.
The open file pointer must have methods write(), tell(), seek(), and
close().

This returns an instance of a class with the following public methods:
      setnchannels(n) -- set the number of channels
      setsampwidth(n) -- set the sample width
      setframerate(n) -- set the frame rate
      setnframes(n)   -- set the number of frames
      setcomptype(type, name)
                      -- set the compression type and the
                         human-readable compression type
      setparams(tuple)
                      -- set all parameters at once
      tell()          -- return current position in output file
      writeframesraw(data)
                      -- write audio frames without pathing up the
                         file header
      writeframes(data)
                      -- write audio frames and patch up the file header
      close()         -- patch up the file header and close the
                         output file
You should set the parameters before the first writeframesraw or
writeframes.  The total number of frames does not need to be set,
but when it is set to the correct value, the header does not have to
be patched up.
It is best to first set all parameters, perhaps possibly the
compression type, and then write audio frames using writeframesraw.
When all frames have been written, either call writeframes(b'') or
close() to patch up the sizes in the header.
The close() method is called automatically when the class instance
is destroyed.
"""

import builtins

__all__ = ["open", "openfp", "Error", "Wave_write"]

class Error(Exception):
    pass

WAVE_FORMAT_PCM = 0x0001
WAVE_FORMAT_IMA_ADPCM = 0x0011
WAVE_FORMAT_XBOX_ADPCM = 0x0069

_array_fmts = None, 'b', 'h', None, 'i'

import audioop
import struct
import sys
from chunk import Chunk
from collections import namedtuple

_wave_params = namedtuple('_wave_params',
                     'nchannels sampwidth framerate nframes comptype compname')

class Wave_write:
    """Variables used in this class:

    These variables are user settable through appropriate methods
    of this class:
    _file -- the open file with methods write(), close(), tell(), seek()
              set through the __init__() method
    _comptype -- the AIFF-C compression type ('NONE' in AIFF)
              set through the setcomptype() or setparams() method
    _compname -- the human-readable AIFF-C compression type
              set through the setcomptype() or setparams() method
    _nchannels -- the number of audio channels
              set through the setnchannels() or setparams() method
    _sampwidth -- the number of bytes per audio sample
              set through the setsampwidth() or setparams() method
    _framerate -- the sampling frequency
              set through the setframerate() or setparams() method
    _nframes -- the number of audio frames written to the header
              set through the setnframes() or setparams() method

    These variables are used internally only:
    _datalength -- the size of the audio samples written to the header
    _nframeswritten -- the number of frames actually written
    _datawritten -- the size of the audio samples actually written
    """

    def __init__(self, f):
        self._i_opened_the_file = None
        if isinstance(f, str):
            f = builtins.open(f, 'wb')
            self._i_opened_the_file = f
        try:
            self.initfp(f)
        except:
            if self._i_opened_the_file:
                f.close()
            raise

    def initfp(self, file):
        self._file = file
        self._convert = None
        self._format = 0
        self._extra = 0
        self._nchannels = 0
        self._sampwidth = 0
        self._framerate = 0
        self._nframes = 0
        self._nframeswritten = 0
        self._datawritten = 0
        self._datalength = 0
        self._headerwritten = False

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    #
    # User visible methods.
    #
    def setnchannels(self, nchannels):
        if self._datawritten:
            raise Error('cannot change parameters after starting to write')
        if nchannels < 1:
            raise Error('bad # of channels')
        self._nchannels = nchannels

    def getnchannels(self):
        if not self._nchannels:
            raise Error('number of channels not set')
        return self._nchannels

    def setformat(self, format):
        if self._datawritten:
            raise Error('cannot change parameters after starting to write')
        self._format = format

    def getformat(self):
        if not self._format:
            raise Error('format not set')
        return self._format

    def setsampwidth(self, sampwidth):
        if self._datawritten:
            raise Error('cannot change parameters after starting to write')
        if sampwidth < 1 or sampwidth > 4:
            raise Error('bad sample width')
        self._sampwidth = sampwidth

    def getsampwidth(self):
        if not self._sampwidth:
            raise Error('sample width not set')
        return self._sampwidth

    def setframerate(self, framerate):
        if self._datawritten:
            raise Error('cannot change parameters after starting to write')
        if framerate <= 0:
            raise Error('bad frame rate')
        self._framerate = int(round(framerate))

    def getframerate(self):
        if not self._framerate:
            raise Error('frame rate not set')
        return self._framerate

    def setnframes(self, nframes):
        if self._datawritten:
            raise Error('cannot change parameters after starting to write')
        self._nframes = nframes

    def getnframes(self):
        return self._nframeswritten

    def setcomptype(self, comptype, compname):
        if self._datawritten:
            raise Error('cannot change parameters after starting to write')
        if comptype not in ('NONE',):
            raise Error('unsupported compression type')
        self._comptype = comptype
        self._compname = compname

    def getcomptype(self):
        return self._comptype

    def getcompname(self):
        return self._compname

    def setparams(self, params):
        nchannels, sampwidth, framerate, nframes, comptype, compname = params
        if self._datawritten:
            raise Error('cannot change parameters after starting to write')
        self.setnchannels(nchannels)
        self.setsampwidth(sampwidth)
        self.setframerate(framerate)
        self.setnframes(nframes)
        self.setcomptype(comptype, compname)

    def getparams(self):
        if not self._nchannels or not self._sampwidth or not self._framerate:
            raise Error('not all parameters set')
        return _wave_params(self._nchannels, self._sampwidth, self._framerate,
              self._nframes, self._comptype, self._compname)

    def setmark(self, id, pos, name):
        raise Error('setmark() not supported')

    def getmark(self, id):
        raise Error('no marks')

    def getmarkers(self):
        return None

    def tell(self):
        return self._nframeswritten

    def writeframesraw(self, data):
        if not isinstance(data, (bytes, bytearray)):
            data = memoryview(data).cast('B')
        self._ensure_header_written(len(data))
        #FIXME: Who cares?!
        nframes = len(data) // (self._sampwidth * self._nchannels)
        #FIXME: Remove this stupid feature
        if self._convert:
            data = self._convert(data)
        #FIXME: Handle this for ADPCM
        if self._sampwidth != 1 and sys.byteorder == 'big':
            data = audioop.byteswap(data, self._sampwidth)
        self._file.write(data)
        self._datawritten += len(data)
        self._nframeswritten = self._nframeswritten + nframes

    def writeframes(self, data):
        self.writeframesraw(data)
        if self._datalength != self._datawritten:
            self._patchheader()

    def close(self):
        try:
            if self._file:
                self._ensure_header_written(0)
                if self._datalength != self._datawritten:
                    self._patchheader()
                self._file.flush()
        finally:
            self._file = None
            file = self._i_opened_the_file
            if file:
                self._i_opened_the_file = None
                file.close()

    #
    # Internal methods.
    #

    def _ensure_header_written(self, datasize):
        if not self._headerwritten:
            if not self._nchannels:
                raise Error('# channels not specified')
            if not self._format:
                raise Error('format not specified')
            if not self._sampwidth:
                raise Error('sample width not specified')
            if not self._framerate:
                raise Error('sampling rate not specified')
            self._write_header(datasize)

    def _write_header(self, initlength):
        assert not self._headerwritten
        self._file.write(b'RIFF')
        if not self._nframes:
            self._nframes = initlength // (self._nchannels * self._sampwidth)
        self._datalength = self._nframes * self._nchannels * self._sampwidth
        try:
            self._form_length_pos = self._file.tell()
        except (AttributeError, OSError):
            self._form_length_pos = None
        self._extra = 0
        if self._format == WAVE_FORMAT_PCM:
          bits_per_sample = self._sampwidth * 8
          block_align = self._sampwidth * self._nchannels
          bytes_per_sec = self._nchannels * self._framerate * self._sampwidth
          self._extra = 0
        elif self._format == WAVE_FORMAT_XBOX_ADPCM or self._format == WAVE_FORMAT_IMA_ADPCM:
          bits_per_sample = 4
          block_align = 0x24 * self._nchannels # No idea where the 0x24 comes from tbh..
          bytes_per_sec = self._framerate * block_align // 64
          self._extra = 4
        else:
          raise Error('format not supported')
        self._file.write(struct.pack('<L4s4sLHHLLHH',
            36+self._datalength + self._extra, b'WAVE', b'fmt ', 16 + self._extra,
            self._format, self._nchannels, self._framerate,
            bytes_per_sec,
            block_align,
            bits_per_sample))
        if self._format == WAVE_FORMAT_XBOX_ADPCM or self._format == WAVE_FORMAT_IMA_ADPCM:
          self._file.write(struct.pack('<HH',
              2, 0x40))
        self._file.write(struct.pack('<4s',
            b'data'))
        if self._form_length_pos is not None:
            self._data_length_pos = self._file.tell()
        self._file.write(struct.pack('<L', self._datalength))
        self._headerwritten = True

    def _patchheader(self):
        assert self._headerwritten
        if self._datawritten == self._datalength:
            return
        curpos = self._file.tell()
        self._file.seek(self._form_length_pos, 0)
        self._file.write(struct.pack('<L', 36 + self._extra + self._datawritten))
        self._file.seek(self._data_length_pos, 0)
        self._file.write(struct.pack('<L', self._datawritten))
        self._file.seek(curpos, 0)
        self._datalength = self._datawritten

def open(f, mode=None):
    if mode is None:
        if hasattr(f, 'mode'):
            mode = f.mode
        else:
            mode = 'wb'
    elif mode in ('w', 'wb'):
        return Wave_write(f)
    else:
        raise Error("mode must be 'w', or 'wb'")

openfp = open # B/W compatibility
