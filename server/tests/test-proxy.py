import pexpect
import time

def not_encrypted_proxy():
    child_server = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_server --debug --no-ssl --no-api-auth 2>&1 | tee proxy-noenc-server.log"')
    child_server.expect("Listening for connections on 127.0.0.1:1234...")

    time.sleep(5)
    child_user = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_client u --no-ssl 2>&1 | tee proxy-noenc-manager.log""')
    child_device = pexpect.spawn(
        'bash -c "./devices/linux-client/rdfm daemonize --name d1 --no-ssl --no-jwt-auth 2>&1 | tee proxy-noenc-device.log"'
    )

    time.sleep(5)
    child_user.sendline("REQ d1 proxy")
    time.sleep(10)
    child_device.expect_exact("Executing shell")
    child_user.expect(r'{"method":"alert","alert":{"message":"shell ready to connect","port":(\d+)}}')

    regex_obj = child_user.match
    proxy_port = int(regex_obj.group(1))

    child_proxy = pexpect.spawn(f"nc localhost {proxy_port}")
    child_proxy.expect("$")

    child_proxy.close()
    child_device.close()
    child_server.close()

    print("Not encrypted proxy test passed!")

def encrypted_proxy():
    child_server = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_server --debug --no-api-auth 2>&1 | tee proxy-enc-server.log"')
    child_server.expect("Listening for connections on 127.0.0.1:1234...")

    time.sleep(5)
    child_user = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_client u 2>&1 | tee proxy-enc-manager.log"')
    child_device = pexpect.spawn('bash -c "./devices/linux-client/rdfm daemonize --name d1 2>&1 | tee proxy-enc-device.log""')

    time.sleep(5)
    child_user.sendline("REQ d1 proxy")
    time.sleep(10)
    child_device.expect_exact("Executing shell")
    child_user.expect(r'{"method":"alert","alert":{"message":"shell ready to connect","port":(\d+)}}')

    regex_obj = child_user.match
    proxy_port = int(regex_obj.group(1))

    child_proxy = pexpect.spawn(f"openssl s_client -connect localhost:{proxy_port}")
    child_proxy.expect("$")

    child_proxy.close()
    child_device.close()
    child_server.close()

    print("Encrypted proxy test passed!")

def two_proxies():
    child_server = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_server --debug --no-ssl --no-api-auth 2>&1 | tee 2proxy-server.log"')
    child_server.expect("Listening for connections on 127.0.0.1:1234...")

    time.sleep(5)
    child_user = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_client u --no-ssl 2>&1 | tee 2proxy-manager.log"')
    child_device = pexpect.spawn(
        'bash -c "./devices/linux-client/rdfm daemonize --name d1 --no-ssl --no-jwt-auth 2>&1 | tee 2proxy-manager.log"'
    )

    time.sleep(5)
    child_user.sendline("REQ d1 proxy")
    time.sleep(10)
    child_device.expect("Executing shell")
    child_user.expect(r'{"method":"alert","alert":{"message":"shell ready to connect","port":(\d+)}}')

    regex_obj = child_user.match
    proxy_port = int(regex_obj.group(1))

    child_proxy1 = pexpect.spawn(f"nc localhost {proxy_port}")
    child_proxy1.expect("$")
    child_proxy1.sendline("export X=1")

    child_user.sendline("LIST")
    child_user.expect('{"method":"alert","alert":{"devices":\["d1"\]}}')
    time.sleep(5)
    child_user.sendline("REQ d1 proxy")
    time.sleep(10)
    child_device.expect("Executing shell")
    child_user.expect(r'{"method":"alert","alert":{"message":"shell ready to connect","port":(\d+)}}')

    regex_obj = child_user.match
    proxy_port = int(regex_obj.group(1))

    child_proxy2 = pexpect.spawn(f"nc localhost {proxy_port}")
    child_proxy2.expect("$")
    child_proxy2.sendline("export X=2")

    child_proxy1.sendline("echo $X")
    child_proxy1.expect("1")
    child_proxy2.sendline("echo $X")
    child_proxy2.expect("2")

    child_proxy1.close()
    child_proxy2.close()
    child_user.close()
    child_device.close()
    child_server.close()

    print("Two proxies test passed!")

not_encrypted_proxy()
time.sleep(5)
encrypted_proxy()
time.sleep(5)
two_proxies()
