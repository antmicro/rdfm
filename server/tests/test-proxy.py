import pexpect

child_server = pexpect.spawn('python3 server.py')

child_user = pexpect.spawn('python3 client.py USER u')
child_device = pexpect.spawn('python3 client.py DEVICE d1')

child_user.sendline('REQ d1 proxy')
child_user.expect(r"\r {'message': 'connect to shell at (\d+)'}\r\nu > ")

regex_obj = child_user.match
proxy_port = int(regex_obj.group(1))

child_proxy = pexpect.spawn(f'nc localhost {proxy_port}')
child_proxy.expect('$')

print('Proxy test passed!')