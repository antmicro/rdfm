#include <zephyr/dfu/mcuboot.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/reboot.h>

LOG_MODULE_REGISTER(mcumgr_test_app);

int main(void) {
  LOG_INF("Starting MCUmgr RDFM client test app");
  LOG_INF("Build time: " __DATE__ " " __TIME__);
  LOG_INF("Current version: " CONFIG_MCUBOOT_IMGTOOL_SIGN_VERSION);
#if defined(CONFIG_MCUMGR_TRANSPORT_UDP)
  LOG_INF("IPv4 address: " CONFIG_NET_CONFIG_MY_IPV4_ADDR);
#endif

  if (IS_ENABLED(CONFIG_UPDATE_SELF_CONFIRM) && !boot_is_img_confirmed()) {
    int res;

    LOG_INF("Test boot detected. Running self tests");
    k_sleep(K_SECONDS(2));

    if (IS_ENABLED(CONFIG_UPDATE_FORCE_FAIL)) {
      LOG_ERR("Self tests failed. Rebooting to prev version");
      sys_reboot(SYS_REBOOT_COLD);
    }

    LOG_INF("Self tests passed");
    res = boot_write_img_confirmed();
    if (res < 0) {
      LOG_INF("Failed to confirm update. Rebooting to prev version");
      sys_reboot(SYS_REBOOT_COLD);
    }
    LOG_INF("Update confirmed");
  }

  // Simulate real application
  while (1) {
    k_sleep(K_SECONDS(30));
    LOG_INF("Doing something fancy");
  }
  return 0;
}
