import pexpect
import time

child_server = pexpect.spawn('python3 server.py')
child_server.expect('Listening for connections on 127.0.0.1:1234...')

child_user = pexpect.spawn('python3 client.py u')
child_device1 = pexpect.spawn('./device/target/debug/rdfm-device-client --name "d1" --file-metadata=tests/testdata.json')

# check initial info
time.sleep(2)
child_user.sendline('REQ d1 info')
child_user.expect("\r {'method': 'alert', 'alert': {}}\r\nu > ")

# check first device visible
child_user.sendline('REQ d1 update')
time.sleep(2)

child_user.sendline('REQ d1 info')
child_user.expect("{'method': 'alert', 'alert': {'a': 5, 'b': 'foo', 'c': {'d': 'bar', 'e': 2}}}\r\nu > ")

print('Device metadata tests passed!')
