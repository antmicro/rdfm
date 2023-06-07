import pexpect
import time

child_server = pexpect.spawn('python3 server.py')
child_server.expect('Listening for connections on 127.0.0.1:1234...')

child_user = pexpect.spawn('python3 client.py u')
child_device = pexpect.spawn('./device/target/debug/rdfm-device-client --name "d1"')

time.sleep(5)
child_user.sendline('REQ d1 proxy')
time.sleep(3)
child_user.expect(r"\r {'method': 'alert', 'alert': {'message': 'shell ready to connect', 'port': (\d+)}}\r\nu > ")

regex_obj = child_user.match
proxy_port = int(regex_obj.group(1))

child_proxy = pexpect.spawn(f'nc localhost {proxy_port}')
child_proxy.expect('$')

print('Proxy test passed!')
