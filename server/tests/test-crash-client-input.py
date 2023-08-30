import pexpect
import time
import sys

child_server = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_server -debug -no_ssl 2>&1 | tee crash-server.log"')
time.sleep(3)
child_user = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_client u -no_ssl 2>&1 | tee crash-manager.log"')

# check invalid request warning
time.sleep(3)
child_user.sendline("this input should throw a warning testtesttest........")
child_user.expect("Invalid request")

telnet_client = pexpect.spawn('bash -c "telnet 127.0.0.1 1234 2>&1 | tee crash-telnet.log"')
telnet_client.sendline("server should not crash test test")

# check server replying
time.sleep(1)
child_user.sendline("LIST")
child_user.expect_exact('{"method":"alert","alert":{"devices":[]}}')

print("Invalid user input crash test passed!")