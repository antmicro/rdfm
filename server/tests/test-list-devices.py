import pexpect
import time

child_server = pexpect.spawn('python3 -m rdfm_mgmt_server -no_ssl')
child_server.expect_exact('Listening for connections on 127.0.0.1:1234...')

child_user = pexpect.spawn('python3 -m rdfm_mgmt_client u -no_ssl')

# check no devices visible
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \[\]}}\r\nu > ")
pexpect.spawn("curl http://127.0.0.1:5000/").expect_exact("[]")

# check first device visible
child_device1 = pexpect.spawn('./device/target/debug/rdfm_mgmt_device --name "d1" --no-ssl')
time.sleep(1)
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \['d1'\]}}\r\nu > ")
pexpect.spawn("curl http://127.0.0.1:5000/").expect('["d1"]')

# check second device visible
child_device2 = pexpect.spawn('./device/target/debug/rdfm_mgmt_device --name "d2" --no-ssl')
time.sleep(1)
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \['d1', 'd2'\]}}\r\nu > ")
pexpect.spawn("curl http://127.0.0.1:5000/").expect('["d1", "d2"]')

# check second device disconnected and not visible
child_device2.close()
time.sleep(1)
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \['d1'\]}}\r\nu > ")

print('List devices test passed!')
