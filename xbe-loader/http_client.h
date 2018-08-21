#ifndef __HTTP_CLIENT_H__
#define __HTTP_CLIENT_H__

void http_client_request(const char* host, unsigned short host_port, const char* abs_path, const char* request_header,
  void(*header_callback)(const char* field, const char* value, void* user),
  void(*message_callback)(unsigned long long offset, const void* buffer, unsigned long long length, void* user),
  void(*close_callback)(void* user),
  void(*error_callback)(void* user),
  void* user
);

#endif
