# Put the IP address of your FTP enabled xbox here
XBOX=192.168.177.80
XBOX_PATH=/E/Games/xqemu-tools-dump-xbox

#OpenXDK path
PREFIX=.

# Your 32 bit Windows compiler
CC = i686-w64-mingw32-gcc

# Path to CXBE
CXBE = bin/cxbe

# ---

#SDLFLAGS = -DENABLE_XBOX -DDISABLE_CDROM 

CC_FLAGS = -m32 -march=i386 -O0 -g -shared -std=gnu99 -ffreestanding -nostdlib -fno-builtin -fno-exceptions # $(SDLFLAGS)
INCLUDE  = -I$(PREFIX)/i386-pc-xbox/include -I$(PREFIX)/include #-I$(PREFIX)/include/SDL

CLINK = -nostdlib -m32 -march=i386 -O0 -g 
ALIGN = -Wl,--file-alignment,0x20 -Wl,--section-alignment,0x20 
SHARED = -shared
ENTRYPOINT = -Wl,--entry,_WinMainCRTStartup 
STRIP = # -Wl,--strip-all 
LD_FLAGS = -m32 -march=i386 -O0 $(CLINK) $(ALIGN) $(SHARED) $(ENTRYPOINT) $(STRIP)
LD_DIRS = -L$(PREFIX)/i386-pc-xbox/lib -L$(PREFIX)/lib 
LD_LIBS  = $(LD_DIRS) -lopenxdk -lhal -lusb -lc -lhal -lc -lxboxkrnl #-lSDL 

# ---

all: default.xbe

# Upload program to xbox
transfer: default.xbe
	wput -u ftp://xbox:xbox@$(XBOX):21/E/Games/xqemu-tools-dump-xbox/default.xbe default.xbe

# Download dumped files from xbox
get:
	@wget -q -O flash.bin ftp://xbox:xbox@$(XBOX):21$(XBOX_PATH)/flash.bin
	@wget -q -O eeprom.bin ftp://xbox:xbox@$(XBOX):21$(XBOX_PATH)/eeprom.bin
	@wget -q -O hdd_0x0-0x3ff.bin ftp://xbox:xbox@$(XBOX):21$(XBOX_PATH)/hdd_0x0-0x3ff.bin

# Test to see if turning on / off the MCPX works
cmp:
	@wget -q -O mcpx-on.bin ftp://xbox:xbox@$(XBOX):21$(XBOX_PATH)/mcpx-on.bin
	@wget -q -O mcpx-off.bin ftp://xbox:xbox@$(XBOX):21$(XBOX_PATH)/mcpx-off.bin
	md5sum mcpx-on.bin mcpx-off.bin

# Download and display log
log:
	@echo "---"
	@wget -q -O - ftp://xbox:xbox@$(XBOX):21$(XBOX_PATH)/log.txt
	@echo "---"

.c.o: reboot.h
	$(CC) -c $< $(CC_FLAGS) $(INCLUDE)

default.exe: dump-xbox.o
	$(CC) -o $@ $< $(LD_LIBS) $(LD_FLAGS)

default.xbe: default.exe
	$(CXBE) -MODE:DEBUG -TITLE:"XQEMU-Tools: dump-xbox" -DUMPINFO:"cxbe.txt" -OUT:"$@" $< > /dev/null

clean: 
	rm -f *.o *.exe *.dll *.xbe *.cxbe cxbe.txt
