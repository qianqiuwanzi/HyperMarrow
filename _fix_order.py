#!/usr/bin/env python3
"""Fix WeChat Pay out_trade_no length on server"""
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('106.55.169.92', username='ubuntu', password='Qianshi54321', timeout=15)

# Read main.py
_, out, _ = c.exec_command('cat /opt/hypermarrow/license_server/main.py')
content = out.read().decode()

# Replace too-long out_trade_no formats with short ones (<32 chars)
fixes = [
    # v2 client pay create
    ('out_trade_no = f"CLIENT-{request.plan.upper()}-{now}-{secrets.token_hex(3)}"',
     'out_trade_no = f"HM-{secrets.token_hex(10)}"'),
    # v2 renew client
    ('out_trade_no = f"RENEW-CLIENT-{active_lic.license_key}-{now}-{secrets.token_hex(3)}"',
     'out_trade_no = f"RC-{secrets.token_hex(10)}"'),
    # v1 pay create
    ('out_trade_no = f"HM-{request.plan.upper()}-{now}-{secrets.token_hex(3)}"',
     'out_trade_no = f"HMV1-{secrets.token_hex(10)}"'),
    # v1 renew
    ('out_trade_no = f"RENEW-{license_key}-{int(time.time())}-{secrets.token_hex(3)}"',
     'out_trade_no = f"RV-{secrets.token_hex(10)}"'),
]

for old, new in fixes:
    if old in content:
        content = content.replace(old, new)
        print(f"Fixed: {old[:60]}...")
    else:
        print(f"NOT FOUND: {old[:60]}...")

# Upload fixed file
sftp = c.open_sftp()
with sftp.file('/opt/hypermarrow/license_server/main.py', 'w') as f:
    f.write(content)
sftp.close()
print("Uploaded main.py")

# Rebuild Docker
_, out, err = c.exec_command('cd /opt/hypermarrow/license_server && sudo docker compose -f docker-compose.yml up -d --build 2>&1')
output = out.read().decode()
print(output[-1500:])

c.close()
print("Done")
