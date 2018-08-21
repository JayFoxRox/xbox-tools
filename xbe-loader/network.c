#include "lwip/tcp.h"
#include "lwip/opt.h"
#include "lwip/arch.h"
#include "lwip/api.h"
#include "lwip/debug.h"
#include "lwip/dhcp.h"
#include "lwip/init.h"
#include "lwip/netif.h"
#include "lwip/sys.h"
#include "lwip/tcpip.h"
#include "lwip/timers.h"
#include "netif/etharp.h"
#include "pktdrv.h"


#define USE_DHCP         0
#define PKT_TMR_INTERVAL 1 /* ms */
#define DEBUGGING        0



struct netif *g_pnetif;
err_t nforceif_init(struct netif *netif);


static struct netif nforce_netif;

static void packet_timer(void *arg);

static void tcpip_init_done(void *arg)
{
	sys_sem_t *init_complete = arg;
	sys_sem_signal(init_complete);
}

static void packet_timer(void *arg)
{
  LWIP_UNUSED_ARG(arg);
  Pktdrv_ReceivePackets();
  sys_timeout(PKT_TMR_INTERVAL, packet_timer, NULL);
}

int network_setup() {

	sys_sem_t init_complete;
	const ip4_addr_t *ip;


#if DEBUGGING
	asm volatile ("jmp .");
	debug_flags = LWIP_DBG_ON;
#else
	debug_flags = 0;
#endif


static ip4_addr_t ipaddr, netmask, gw;
#if USE_DHCP
	IP4_ADDR(&gw, 0,0,0,0);
	IP4_ADDR(&ipaddr, 0,0,0,0);
	IP4_ADDR(&netmask, 0,0,0,0);
#else
	IP4_ADDR(&gw, 192,168,177,1);
	IP4_ADDR(&ipaddr, 192,168,177,3);
	IP4_ADDR(&netmask, 255,255,255,0);
#endif



	/* Initialize the TCP/IP stack. Wait for completion. */
	sys_sem_new(&init_complete, 0);
	tcpip_init(tcpip_init_done, &init_complete);
	sys_sem_wait(&init_complete);
	sys_sem_free(&init_complete);

	g_pnetif = netif_add(&nforce_netif, &ipaddr, &netmask, &gw,
	                     NULL, nforceif_init, ethernet_input);
	if (!g_pnetif) {
		return -1;
	}

	netif_set_default(g_pnetif);
	netif_set_up(g_pnetif);

#if USE_DHCP
	dhcp_start(g_pnetif);
#endif

	packet_timer(NULL);

#if USE_DHCP
	debugPrint("Waiting for DHCP...\n");
	while (g_pnetif->dhcp->state != DHCP_STATE_BOUND) {
		NtYieldExecution();
  }
	debugPrint("DHCP bound!\n");
#endif

	debugPrint("\n");
	debugPrint("IP address.. %s\n", ip4addr_ntoa(netif_ip4_addr(g_pnetif)));
	debugPrint("Mask........ %s\n", ip4addr_ntoa(netif_ip4_netmask(g_pnetif)));
	debugPrint("Gateway..... %s\n", ip4addr_ntoa(netif_ip4_gw(g_pnetif)));
	debugPrint("\n");

  return 0;
}

void network_cleanup() {
	Pktdrv_Quit();
}
