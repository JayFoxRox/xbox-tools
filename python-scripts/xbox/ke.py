from .interface import api
from . import pe
import struct

SCSI_IOCTL_DATA_OUT         = 0
SCSI_IOCTL_DATA_IN          = 1
SCSI_IOCTL_DATA_UNSPECIFIED = 2

IOCTL_SCSI_PASS_THROUGH        = 0x4D004
IOCTL_SCSI_PASS_THROUGH_DIRECT = 0x4D014

NULL = 0

FALSE = 0x00000000
TRUE  = 0x00000001 # FIXME: Check if these are correct!

def AvSendTVEncoderOption(RegisterBase, Option, Param, Result):
  #IN PVOID RegisterBase,
  #IN ULONG Option,
  #IN ULONG Param,
  #OUT PULONG Result
  call_stdcall(2, "<IIII", RegisterBase, Option, Param, Result)

def IoDeviceObjectType():
  return pe.resolve_export(70)

def IoSynchronousDeviceIoControlRequest(IoControlCode, DeviceObject, InputBuffer, InputBufferLength, OutputBuffer, OutputBufferLength, ReturnedOutputBufferLength, InternalDeviceIoControl):
  #IN ULONG IoControlCode,
  #IN PDEVICE_OBJECT DeviceObject,
  #IN PVOID InputBuffer OPTIONAL,
  #IN ULONG InputBufferLength,
  #OUT PVOID OutputBuffer OPTIONAL,
  #IN ULONG OutputBufferLength,
  #OUT PULONG ReturnedOutputBufferLength OPTIONAL,
  #IN BOOLEAN InternalDeviceIoControl) # FIXME: How to handle this one properly? xxxB? Bxxx? I?
  return call_stdcall(84, "<IIIIIIII", IoControlCode, DeviceObject, InputBuffer, InputBufferLength, OutputBuffer, OutputBufferLength, ReturnedOutputBufferLength, InternalDeviceIoControl)

def MmAllocateContiguousMemory(NumberOfBytes):
  return call_stdcall(165, "<I", NumberOfBytes)

def MmFreeContiguousMemory(BaseAddress):
  return call_stdcall(171, "<I", BaseAddress)

def MmGetPhysicalAddress(BaseAddress):
  return call_stdcall(173, "<I", BaseAddress)

def ObReferenceObjectByName(ObjectName, Attributes, ObjectType, ParseContext, Object):
  #IN POBJECT_STRING ObjectName,
  #IN ULONG Attributes,
  #IN POBJECT_TYPE ObjectType,
  #IN OUT PVOID ParseContext OPTIONAL,
  #OUT PVOID *Object
  return call_stdcall(247, "<IIIII", ObjectName, Attributes, ObjectType, ParseContext, Object)

def RtlInitAnsiString(DestinationString, SourceString):
  #IN OUT PANSI_STRING DestinationString,
  #IN PCSZ SourceString
  return call_stdcall(289, "<II", DestinationString, SourceString)

def call_stdcall(function, types, *arguments):
  address = pe.resolve_export(function)
  registers = api.call(address, struct.pack(types, *arguments))
  return registers['eax']
