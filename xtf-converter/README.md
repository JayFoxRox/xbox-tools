A tool to convert [XTF fonts](http://xboxdevwiki.net/xtf) to SVG fonts.

This tool has been designed for "Xbox.xtf" and "XBox Book.xtf" dashboard-files.

# Usage

```
./main.py "Xbox.xtf" > "Xbox.svg"
./main.py "XBox Book.xtf" > "XBox Book.svg"
```

# Optional: Convert SVG fonts to TTF

First, install svg2ttf:

```
npm install -g svg2ttf
```

Then convert the files:

```
svg2ttf "Xbox.svg" "Xbox.ttf"
svg2ttf "XBox Book.svg" "XBox Book.ttf"
```

You can then open "display-ttf.html" in your browser to see the fonts.
