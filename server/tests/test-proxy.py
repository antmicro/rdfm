import pexpect
import time

def not_encrypted_proxy():
    child_server = pexpect.spawn('python3 -m rdfm_mgmt_server -no_ssl')
    child_server.expect('Listening for connections on 127.0.0.1:1234...')

    child_user = pexpect.spawn('python3 -m rdfm_mgmt_client u')
    child_device = pexpect.spawn(
        './device/target/debug/rdfm_mgmt_device --name "d1" --no-ssl'
)

    time.sleep(5)
    child_user.sendline('REQ d1 proxy')
    time.sleep(3)
    child_user.expect(r"\r {'method': 'alert', 'alert': {'message': 'shell ready to connect', 'port': (\d+)}}\r\nu > ")

    regex_obj = child_user.match
    proxy_port = int(regex_obj.group(1))

    child_proxy = pexpect.spawn(f'nc localhost {proxy_port}')
    child_proxy.expect('$')

    child_proxy.close()
    child_device.close()
    child_server.close()

    print('Not encrypted proxy test passed!')

def encrypted_proxy():
    child_server = pexpect.spawn('python3 -m rdfm_mgmt_server')
    child_server.expect('Listening for connections on 127.0.0.1:1234...')

    child_user = pexpect.spawn('python3 -m rdfm_mgmt_client u')
    child_device = pexpect.spawn('./device/target/debug/rdfm_mgmt_device --name "d1"')

    time.sleep(5)
    child_user.sendline('REQ d1 proxy')
    time.sleep(3)
    child_user.expect(r"\r {'method': 'alert', 'alert': {'message': 'shell ready to connect', 'port': (\d+)}}\r\nu > ")

    regex_obj = child_user.match
    proxy_port = int(regex_obj.group(1))

    child_proxy = pexpect.spawn(f'openssl s_client -connect localhost:{proxy_port}')
    child_proxy.expect('$')

    child_proxy.close()
    child_device.close()
    child_server.close()

    print('Encrypted proxy test passed!')

#not_encrypted_proxy()
pexpect.run("tests/certgen.sh")
#time.sleep(3)
encrypted_proxy()
