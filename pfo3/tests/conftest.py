import sys
from pathlib import Path

# Agregar raíz de pfo3 al sys.path para imports limpios
pfo3_root = Path(__file__).resolve().parent.parent
if str(pfo3_root) not in sys.path:
    sys.path.insert(0, str(pfo3_root))
