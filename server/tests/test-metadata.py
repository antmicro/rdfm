import pexpect
import time

pexpect.run("server/tests/certgen.sh")
time.sleep(3)

child_server = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_server 2>&1 | tee metadata-server.log"')
child_server.expect("Listening for connections on 127.0.0.1:1234...")

child_user = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_client u 2>&1 | tee metadata-manager.log"')
time.sleep(3)
child_user.expect('Connected as u')
child_device = pexpect.spawn("""bash -c \
"./devices/linux-client/rdfm daemonize \
--name d1 \
--no-jwt-auth \
--file-metadata server/tests/testdata.json \
2>&1 | tee metadata-device.log"
""")

# check initial info
time.sleep(5)
child_user.sendline("REQ d1 info")
time.sleep(5)
child_user.expect('{"metadata":{},"capabilities":{"shell_connect":true,"file_transfer":true,"exec_cmds":false}}}')

# check first device visible
child_user.sendline("REQ d1 update")
time.sleep(2)

child_user.sendline("REQ d1 info")
time.sleep(1)
child_user.expect(
    '{"method":"alert","alert":{"metadata":{"a":5,"b":"foo","c":{"d":"bar","e":2}},"capabilities":{"shell_connect":true,"file_transfer":true,"exec_cmds":false}}}'
)

print("Device metadata tests passed!")
