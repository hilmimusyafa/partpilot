from pathlib import Path
import secrets, os, json, importlib.metadata as meta
p=Path('/home/rifqisetiawan/.config/partpilot')
p.mkdir(mode=0o700,parents=True,exist_ok=True)
paths=['demo-db-owner-password','demo-runtime.env','demo-worker.env']
if any((p/x).exists() for x in paths):
    raise RuntimeError('Deployment secrets already exist; refusing replacement')
owner=secrets.token_urlsafe(36);api=secrets.token_urlsafe(36);worker=secrets.token_urlsafe(36);login=secrets.token_urlsafe(18)
def write(name,content):
    fd=os.open(p/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(content)
write(paths[0],owner)
write(paths[1],f'DATABASE_URL=postgresql://pp_demo_api:{api}@127.0.0.1:55438/partpilot_demo\nPARTPILOT_DEMO_PASSWORD={login}\nPARTPILOT_PUBLIC_ORIGIN=https://partpilot.rifqisetiawan.my.id\n')
write(paths[2],f'DATABASE_URL=postgresql://pp_demo_worker:{worker}@127.0.0.1:55438/partpilot_demo\n')
print('Scoped credentials created; contents not printed.')

