import pexpect
import time

pexpect.run("tests/certgen.sh")
time.sleep(3)

child_server = pexpect.spawn('python3 -m rdfm_mgmt_server')

time.sleep(3)
child_user = pexpect.spawn('python3 -m rdfm_mgmt_client u')
child_user.expect('u > ')
child_device1 = pexpect.spawn(
    '''./device/target/debug/rdfm_mgmt_device --name "d1"
    --file-metadata=tests/testdata.json'''
)

child_user.sendline('REQ d1 upload rdm.md README.md')
time.sleep(10)
diff = pexpect.spawn('diff rdm.md README.md')
time.sleep(5)
diff.close()
assert diff.exitstatus == 0
time.sleep(5)
pexpect.spawn('rm rdm.md')

print('File upload test passed!')

child_user.sendline('REQ d1 download device/target/debug/rdfm_mgmt_device.d')
time.sleep(10)
diff = pexpect.spawn('diff rdfm_mgmt_device.d device/target/debug/rdfm_mgmt_device.d')
time.sleep(5)
diff.close()
assert diff.exitstatus == 0
time.sleep(5)
pexpect.spawn('rm rdfm_mgmt_device.d')

print('File download test passed!')