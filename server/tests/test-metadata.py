import pexpect
import time

pexpect.run("server/tests/certgen.sh")
time.sleep(3)

child_server = pexpect.spawn("python3 -m rdfm_mgmt_server")
child_server.expect("Listening for connections on 127.0.0.1:1234...")

child_user = pexpect.spawn("python3 -m rdfm_mgmt_client u")
time.sleep(3)
child_user.expect('{"method":"alert","alert":{"message":"Connected as u"}}')
child_device = pexpect.spawn(
    """./devices/linux-client/rdfm daemonize --name d1
    --file-metadata server/tests/testdata.json"""
)
child_device.expect("Got JWT token!")

# check initial info
time.sleep(5)
child_user.sendline("REQ d1 info")
time.sleep(5)
child_user.expect('{"metadata":{},"capabilities":{"shell_connect":true,"file_transfer":true,"exec_cmds":false}}}\r\nu > ')

# check first device visible
child_user.sendline("REQ d1 update")
time.sleep(2)

child_user.sendline("REQ d1 info")
time.sleep(1)
child_user.expect(
    '{"method":"alert","alert":{"metadata":{"a":5,"b":"foo","c":{"d":"bar","e":2}},"capabilities":{"shell_connect":true,"file_transfer":true,"exec_cmds":false}}}\r\nu > '
)

print("Device metadata tests passed!")
