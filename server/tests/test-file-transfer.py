import pexpect
import os
import time
import filecmp
import requests

time.sleep(3)
cache_dir = 'server_file_cache'

child_server = pexpect.spawn(f'bash -c "python3 -m rdfm_mgmt_server --debug --no-api-auth --cache-dir {cache_dir} 2>&1 | tee filetx-server.log"')
#print('Cache directory:', os.system(f'find / -name "{cache_dir}" -type d'))
child_server.expect_exact('Running on https://127.0.0.1:5000')

child_user = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_client u 2>&1 | tee filetx-manager.log"')
child_user.expect_exact("Connected as u")

child_device = pexpect.spawn('bash -c "./devices/linux-client/rdfm daemonize --name d1 2>&1 | tee filetx-device.log"')
child_device.expect_exact('Connected to the server')

### http api test
# download
resp = requests.get('https://127.0.0.1:5000/device/d1/download',
             verify='./certs/CA.crt',
             data={'file_path': 'devices/linux-client/rdfm'})
assert resp.status_code == 200
print(pexpect.run('ls .'))
print(pexpect.run(f'ls {cache_dir}'))
print(pexpect.run(f'ls {cache_dir}/d1'))
with open('rdfm', 'wb') as f:
    f.write(resp.content)
assert filecmp.cmp('rdfm', 'devices/linux-client/rdfm')
print('File download endpoint test passed!')

# upload
resp = requests.post('https://127.0.0.1:5000/device/d1/upload',
                     verify='./certs/CA.crt',
                     files={'file': open('README.md', 'rb')},
                     data={'file_path': 'x'})

assert resp.status_code == 200
print(pexpect.run(f'ls {cache_dir}/d1'))
child_device.expect_exact("Downloaded file")
assert filecmp.cmp('x', 'README.md')
os.remove("x")
print('File upload endpoint test passed!')

### manager tests
# upload
child_user.sendline('REQ d1 upload rdm.md README.md')
child_user.expect_exact("Uploading file...")
child_device.expect_exact("Downloaded file")
print(pexpect.run(f'ls {cache_dir}/d1'))
diff = filecmp.cmp('rdm.md', 'README.md')
assert diff
os.remove("rdm.md")
print('File upload test passed!')

# download
#pexpect.spawn('head devices/linux-client/rdfm > devices/linux-client/rdfm_head')
child_user.sendline('REQ d1 download devices/linux-client/rdfm')
child_user.expect_exact("Downloading file...")
child_device.expect_exact("Received upload request of file")
child_device.expect_exact("Uploaded file")
print(pexpect.run(f'ls {cache_dir}/d1'))
diff = filecmp.cmp('rdfm', 'devices/linux-client/rdfm')
assert diff
os.remove("rdfm")
print('File download test passed!')