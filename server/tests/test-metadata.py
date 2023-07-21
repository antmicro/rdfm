import pexpect
import time

pexpect.run("tests/certgen.sh")
time.sleep(3)

child_server = pexpect.spawn("python3 -m rdfm_mgmt_server")
child_server.expect_exact("Listening for connections on 127.0.0.1:1234...")

child_user = pexpect.spawn("python3 -m rdfm_mgmt_client u")
time.sleep(1)
child_user.expect('{"method":"alert","alert":{"message":"Connected as u"}}')
child_device1 = pexpect.spawn(
    """./device/target/debug/rdfm_mgmt_device --name "d1"
    --file-metadata=tests/testdata.json"""
)

# check initial info
time.sleep(2)
child_user.sendline("REQ d1 info")
time.sleep(1)
child_user.expect('{"method":"alert","alert":{"metadata":{},"capabilities":{"shell_connect":false,"file_transfer":false,"exec_cmds":false}}}\r\nu > ')

# check first device visible
child_user.sendline("REQ d1 update")
time.sleep(2)

child_user.sendline("REQ d1 info")
time.sleep(1)
child_user.expect(
    '{"method":"alert","alert":{"metadata":{"a":5,"b":"foo","c":{"d":"bar","e":2}},"capabilities":{"shell_connect":false,"file_transfer":false,"exec_cmds":false}}}\r\nu > '
)

print("Device metadata tests passed!")
