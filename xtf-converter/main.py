#!/bin/env python3

import sys
import struct
import os

fontPath = sys.argv[1]

with open(fontPath, 'rb') as f:
  magic = f.read(4)
  string_len = struct.unpack("I", f.read(4))[0]
  string = f.read(string_len).decode('ascii').rstrip('\0')

  # I assume this string is the font-name
  fontName = string

  print('<?xml version="1.0" standalone="yes"?>')
  print('<svg width="100%" height="100%" version="1.1" xmlns = "http://www.w3.org/2000/svg">')
  print('  <defs>')
  #FIXME: All these numbers below!
  print('    <font id="font" horiz-adv-x="1000">')
  #FIXME: Escape font name
  print('      <font-face font-family="' + fontName + '">')
  print('        <font-face-src>')
  print('          <font-face-name name="' + fontName + '"/>')
  print('        </font-face-src>')
  print('      </font-face>')
  #FIXME: Is there a better symbol we could use?!
  print('      <missing-glyph><path d="M0,0h200v200h-200z"/></missing-glyph>')
  #print('      <glyph unicode="@"><!-- Outline of @ glyph --></glyph>')

  # https://msdn.microsoft.com/en-us/library/dd144956%28v=vs.85%29.aspx
  cursor = f.tell()
  cbThis = struct.unpack("I", f.read(4))[0] #FIXME: Is this the one being exploited?! If so, log something!
  flAccel = struct.unpack("I", f.read(4))[0]
  assert(flAccel == 0)
  cGlyphsSupported = struct.unpack("I", f.read(4))[0]
  print("<!-- " + str(cGlyphsSupported) + " glyphs supported -->")
  cRanges = struct.unpack("I", f.read(4))[0]
  ranges = []
  for i in range(cRanges):
    wcLow = struct.unpack("H", f.read(2))[0]
    cGlyphs = struct.unpack("H", f.read(2))[0]
    ranges.append((wcLow, cGlyphs))
  assert(f.tell() == (cursor + cbThis))

  metrics = []
  for i in range(cGlyphsSupported):

    # https://msdn.microsoft.com/en-us/library/windows/desktop/dd374209(v=vs.85).aspx
    gmfBlackBoxX = struct.unpack("f", f.read(4))[0]
    gmfBlackBoxY = struct.unpack("f", f.read(4))[0]
    gmfptGlyphOrigin = struct.unpack(">ff", f.read(8))
    gmfCellIncX = struct.unpack("f", f.read(4))[0]
    gmfCellIncY = struct.unpack("f", f.read(4))[0]
    metrics.append((gmfBlackBoxX, gmfBlackBoxY, gmfptGlyphOrigin, gmfCellIncX, gmfCellIncY))

    offset = struct.unpack("I", f.read(4))[0] #FIXME: assert(...) that this points at the index_count of the glyph

  glyphIndex = 0
  for r in ranges:
    print("<!-- Decoding " + str(r[1]) + " symbols -->")
    for c in range(r[0], r[0] + r[1]):

      (gmfBlackBoxX, gmfBlackBoxY, gmfptGlyphOrigin, gmfCellIncX, gmfCellIncY) = metrics[glyphIndex]
      glyphIndex += 1

      symbol = struct.pack('H', c).decode("utf-16")

      print("<!-- Decoding symbol " + str(c) + ": \"" + symbol + "\" -->")

      symbol = "&#x%04X;" % c

      index_count = struct.unpack("H", f.read(2))[0]
      vertex_count = struct.unpack("H", f.read(2))[0]
      indices = []
      for i in range(index_count):
        indices.append(struct.unpack("H", f.read(2))[0])
      vertices = []
      for i in range(vertex_count):
        vertices.append((struct.unpack("f", f.read(4))[0], struct.unpack("f", f.read(4))[0]))

      scale = 1000

      def strf(f):
        return str(int(f * scale))


      # The following values can not (easily) be used in svg fonts; so we need them to be zero
      # We use 0.5 as threshold
      eps = 0.5 / scale

      if (gmfCellIncY >= eps):
        print("<!-- y-inc: " + str(gmfCellIncY) + " -->")
        assert(False)

      if (gmfptGlyphOrigin[0] >= eps):
        print("<!-- x-orig: " + str(gmfptGlyphOrigin[0]) + " -->")
        assert(False)

      if (gmfptGlyphOrigin[1] >= eps):
        print("<!-- y-orig: " + str(gmfptGlyphOrigin[1]) + " -->")
        assert(False)



      path = ""

      #FIXME: Optimize this [so it generates shorter / more clever path]
      assert(len(indices) % 3 == 0)
      for i in range(len(indices) // 3):
        x = (
          strf(vertices[indices[i*3+0]][0]),
          strf(vertices[indices[i*3+1]][0]),
          strf(vertices[indices[i*3+2]][0]),
        )
        y = (
          strf(vertices[indices[i*3+0]][1]),
          strf(vertices[indices[i*3+1]][1]),
          strf(vertices[indices[i*3+2]][1]),
        )
        path += "M" + x[0] + "," + y[0]
        path += "L" + x[1] + "," + y[1]
        path += "L" + x[2] + "," + y[2]
        path += "z"

      print('      <glyph unicode="' + symbol + '" horiz-adv-x="' + strf(gmfCellIncX) + '" d="' + path + '"></glyph>')

    # Hack to only export first range
    if False:
      f.seek(0, os.SEEK_END)
      break
  
  cursor = f.tell()
  f.seek(0, os.SEEK_END)
  assert(f.tell() == cursor)

  print('    </font>')
  print('  </defs>')
  print('</svg>')
