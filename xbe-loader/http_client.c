// Inspired by https://github.com/kennethnoyens/lwipHttpClient/blob/master/httpclient.c

#include "lwip/tcp.h"
#include "lwip/opt.h"
#include "lwip/arch.h"
#include "lwip/api.h"
#include "lwip/debug.h"
#include "lwip/init.h"
#include "lwip/netif.h"
#include "lwip/sys.h"
#include "lwip/tcpip.h"

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>


void write_log(const char* format, ...);
#define debugPrint(x, ...) write_log(x, ## __VA_ARGS__)

#define assert(x) if (!(x)) { debugPrint("\nAssert failed '%s' in %s:%d\n\n", #x, __FILE__, __LINE__); }

#include <xboxrt/debug.h>


typedef struct {
  struct tcp_pcb* pcb;
  char* host;
  char* abs_path;
  char* request_header;
  uint64_t message_offset;
  int status;
  bool message_started;
  char* line_buffer;
  unsigned int line_buffer_length;
  unsigned int line_buffer_offset;
  unsigned int timeout;

  void(*header_callback)(const char* field, const char* value, void* user);
  //FIXME: Add a callback for reporting HTTP status and message length
  void(*message_callback)(unsigned long long offset, const void* buffer, unsigned long long length, void* user);
  void(*close_callback)(void* user);
  void(*error_callback)(void* user);
  void* user;

} Request;

static void destroy_request(Request* request) {
	if(request->pcb != NULL) {
		tcp_close(request->pcb);
	}
  //FIXME: Check for null pointers?
  free(request->host);
  free(request->abs_path);
  free(request->request_header);
  free(request);
}

static err_t connected_callback(void *arg, struct tcp_pcb *pcb, err_t err);
static err_t sent_callback(void *arg, struct tcp_pcb *pcb, u16_t len);
static err_t poll_callback(void *arg, struct tcp_pcb *pcb);
static err_t recv_callback(void *arg, struct tcp_pcb *pcb, struct pbuf *p, err_t err);
static void err_callback(void *arg, err_t err);

void http_client_request(const char* host, unsigned short host_port, const char* abs_path, const char* request_header,
  void(*header_callback)(const char* field, const char* value, void* user),
  //FIXME: Add a callback for reporting HTTP status and message length
  void(*message_callback)(unsigned long long offset, const void* buffer, unsigned long long length, void* user),
  void(*close_callback)(void* user),
  void(*error_callback)(void* user),
  void* user
) {
  // Lookup host
  //FIXME: Might want to do this elsewhere?
  ip4_addr_t host_ip;
#if LWIP_DNS
  debugPrint("Resolving hostname '%s'\n", host);
  err_t err = netconn_gethostbyname (host, &host_ip);
  if (err != ERR_OK) {
    assert(false);
  }
#else
	IP4_ADDR(&host_ip, 192,168,177,1);
  host = ip4addr_ntoa(&host_ip);
#endif

  // Keep track of the request in an object
	Request* request = malloc(sizeof(Request));
  if (request == NULL) {
    assert(false);
  }

  // Fill out all state information
  request->host = strdup(host);
  request->abs_path = strdup(abs_path);
  request->request_header = strdup(request_header);
  request->header_callback = header_callback;
  request->message_callback = message_callback;
  request->close_callback = close_callback;
  request->error_callback = error_callback;
  request->message_started = false;
  request->message_offset = 0;
  request->line_buffer = NULL;
  request->line_buffer_offset = 0;
  request->line_buffer_length = 0;
  request->timeout = 0;
  request->user = user;

  debugPrint("Will request '%s' from '%s' (%s) port %d\n", request->abs_path, request->host, ip4addr_ntoa(&host_ip), host_port);

	// Create a new PCB for our request
	request->pcb = tcp_new();
	if(request->pcb == NULL) {
    request->error_callback(request->user);

    destroy_request(request);

    return;
	}
	tcp_arg(request->pcb, request);

  // Search a local port where we can bind successfully
	//FIXME: Can we auto pick this via lwip?
	uint16_t local_port = 4545;
	while(tcp_bind(request->pcb, IP_ADDR_ANY, local_port) != ERR_OK) {
		local_port++;
	}

  // Connect to the server
	tcp_connect(request->pcb, &host_ip, host_port, connected_callback);
}

static err_t connected_callback(void *arg, struct tcp_pcb *pcb, err_t err) {
  Request* request = arg;
  assert(request->pcb == pcb);

  // error?
  if(err != ERR_OK) {
    request->error_callback(request->user);

    destroy_request(request);

    return ERR_OK;
  }

  //FIXME: What prevents us from doing this in the request setup already?
  //       We could save some allocations then
  char* request_str = malloc(1024 + strlen(request->abs_path) + strlen(request->host) + strlen(request->request_header));
  if(request_str == NULL) {
    assert(false);
  }
  sprintf(request_str, "GET %s HTTP/1.1\r\n"
                       "Host: %s\r\n"
                       "Accept-Encoding: identity\r\n"
                       "Connection: close\r\n"
                       "%s\r\n", request->abs_path, request->host, request->request_header);

  // This is in TCP fine grained steps; so roughly 500ms per step
  unsigned int poll_interval = 2;

  // Setup callbacks
  tcp_sent(request->pcb, sent_callback);
  tcp_poll(request->pcb, poll_callback, poll_interval);
  tcp_recv(request->pcb, recv_callback);
  tcp_err(request->pcb, err_callback);

  // Send request
  tcp_write(request->pcb, request_str, strlen(request_str), 1);
  tcp_output(request->pcb);
  debugPrint("Request sent\n");

  //FIXME: Free the stuff we don't need anymore already?

  return ERR_OK;
}

static err_t sent_callback(void *arg, struct tcp_pcb *pcb, u16_t len) {
  Request* request = arg;
  assert(request->pcb == pcb);

  request->timeout = 0;
  return ERR_OK;
}

static err_t poll_callback(void *arg, struct tcp_pcb *pcb) {
  Request* request = arg;
  assert(request->pcb == pcb);

  request->timeout++;

  // Timeout is called roughly every second, so wait 5 seconds
  if(request->timeout >= 5) {
    tcp_abort(pcb);

    request->error_callback(request->user);

    destroy_request(request);
  }

  return ERR_OK;
}


static err_t recv_callback(void *arg, struct tcp_pcb *pcb, struct pbuf *p, err_t err) {
  Request* request = arg;
  assert(request->pcb == pcb);

  debugPrint("recv %d\n", p);

	char * page = NULL;

  if (err != ERR_OK) {
    assert(false);
  }

  if (p != NULL) {


    // Receive data
    tcp_recved(pcb, p->tot_len);

    // Add payload (p) to state
    struct pbuf* temp_p = p;
    while(temp_p != NULL) {

      void* payload = temp_p->payload;
      int len = temp_p->len;

      if (!request->message_started) {

        // Realloc the line buffer if it's too short
        unsigned int required_line_buffer_length = request->line_buffer_offset + len;
        if (required_line_buffer_length > request->line_buffer_length) {
          request->line_buffer = realloc(request->line_buffer, required_line_buffer_length);
          request->line_buffer_length = required_line_buffer_length;
        }

        // Append the payload to the current line buffer
        memcpy(&request->line_buffer[request->line_buffer_offset], payload, len);
        request->line_buffer_offset += len;

        char* line = request->line_buffer;
        char* cr;
        //FIXME: This might go beyond the line buffer!
        while((cr = strchr(line, '\r'))) {

          // Check if this is really CRLF
          if (cr[1] != '\n') {
            line = &cr[1];
            continue;
          }

          // CRLF at line start means that the message should start now
          if (cr == line) {
            assert(request->status != 0);
            request->message_started = true;

            // Skip to next line by skipping CRLF
            line = &cr[2];

            //FIXME: Free request->line_buffer sometime?
            //       We can't do it here, as it's still used after this loop
            break;
          }

          // Replace CR by zero termination, so we can read the string
          cr[0] = '\0';

          debugPrint("Parsing line '%s'\n", line);
          if (request->status == 0) {
            //FIXME: Parse this line instead
            //FIXME: WTF? Why does python return 1.0?
            char status_prefix[] = "HTTP/1.0 ";
            assert(!memcmp(line, status_prefix, sizeof(status_prefix) - 1));

            // Search for ' ' which is the end of the HTTP version string
            char* version_space = strchr(line, ' ');
            assert(version_space != NULL);
            version_space[0] = '\0';

            // Go to the ' ', which is the end of the status code
            char* status_space = strchr(&version_space[1], ' ');
            assert(status_space != NULL);
            status_space[0] = '\0';

            // Get status code
            request->status = atoi(&version_space[1]);
            debugPrint("Got status %d\n", request->status);
          } else {

            // Search for ':' which ends the field and also zero terminate it
            char* colon = strchr(line, ':');
            assert(colon != NULL);
            colon[0] = '\0';

            // We can now get the field from the start of the line
            const char* field = line;

            // Get the value now, but remove the LWS (leading whitespace)
            const char* value = &colon[1];
            //FIXME: Support other whitespaces?
            while(value[0] == ' ' || value[0] == '\t') {
              value++;
            }

            // Do callback
            request->header_callback(field, value, request->user);
          }

          // Skip to next line by skipping CRLF
          line = &cr[2];
        }

        // Remove processed data from line buffer
        debugPrint("Cleaning line buffer\n");
        unsigned int processed_bytes = line - request->line_buffer;
        request->line_buffer_offset -= processed_bytes;
        memmove(request->line_buffer, line, request->line_buffer_offset);

        // Possibly submit all the data which still made it into the line buffer
        debugPrint("Providing remaining payload\n");
        payload = request->line_buffer;
        len = request->line_buffer_offset;
      }

      if (request->message_started && len > 0) {
        debugPrint("Doing message callback\n");
        request->message_callback(request->message_offset, payload, len, request->user);
        request->message_offset += len;
      }

      temp_p = temp_p->next;
    }
    
    // Remove all payloads from the queue
    while(p != NULL) {
      temp_p = p->next;
      pbuf_free(p);
      p = temp_p;
    }

  } else {
    request->close_callback(request->user);

    destroy_request(request);

    return ERR_OK;
  }
 
  return ERR_OK;
}

// Function that lwip calls when there is an error
static void err_callback(void *arg, err_t err) {
  Request* request = arg;

  request->error_callback(request);

  destroy_request(request);
}

