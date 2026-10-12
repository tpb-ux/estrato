"""Datasets diários do Estrato (rodado pela VPS uma vez por dia): Câmara/Senado, CEAP e fotos oficiais."""
import subprocess, sys
for t in ("tools/camara_senado.py", "tools/ceap.py", "tools/fotos.py"):
    r = subprocess.run([sys.executable, t]); print(t, "->", r.returncode)
