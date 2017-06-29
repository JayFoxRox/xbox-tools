# This code is the hack for doing random read/writes using XBDM

Assembled using https://defuse.ca/online-x86-assembler.htm

```
# Disable memory protection
mov eax, cr0
push eax
and eax, 0xFFFEFFFF
mov cr0, eax

# Get arguments
mov edx, [esp+8]        # Get communication address
mov ebx, [edx+0]        # Get address
mov ecx, [edx+4]        # Get operation
mov eax, [edx+8]        # Data; Might need this for writes

read_u8:
loop read_u16 # 1
mov al, [ebx]

read_u16:
loop read_u32 # 2
mov ax, [ebx]

read_u32:
loop write_u8 # 3
mov eax, [ebx]

write_u8:
loop write_u16 # 4
mov [ebx], al

write_u16:
loop write_u32 # 5
mov [ebx], ax

write_u32:
loop cleanup # 6
mov [ebx], eax

cleanup:
mov [edx+8], eax        # Data; Might need this for reads
pop eax                 # Restore cr0 (memory protection)
mov cr0, eax
mov eax, 0x02DB0000     # Return Success (lower bits describe the response type)
ret 4
```

TODO:
As the stack still contains the actual buffer we could send all input data through the stack (with one network packet)
Likewise, the return data could be pushed directly into the return packet
