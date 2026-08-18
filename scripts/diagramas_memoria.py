"""
Genera los diagramas de flujo de la memoria con Graphviz.

Se escriben como codigo y no se dibujan a mano por la misma razon que las
figuras de datos: cuando el sistema cambia, el diagrama se regenera en lugar
de quedarse describiendo una version anterior. Un diagrama desactualizado es
peor que ninguno, porque el lector lo cree.

Convenio de color, constante en los tres:

    azul    componente DETERMINISTA: mismo resultado ante la misma entrada
    rojo    componente ESTOCASTICO: el modelo de lenguaje
    gris    datos y artefactos
    verde   comprobacion automatica

Esa distincion no es decorativa: es la que sostiene el trabajo, porque el
hallazgo central es que la parte estocastica no aporta lo que se esperaba.

Requiere Graphviz instalado y el ejecutable dot en el PATH.

Uso:
    python scripts/diagramas_memoria.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "memoria" / "figuras"

AZUL, ROJO, GRIS, VERDE = "#2E5A88", "#A8322D", "#5B6670", "#3D7A4E"
AZUL_F, ROJO_F, GRIS_F, VERDE_F = "#E8EFF6", "#FBEDEC", "#F0F1F2", "#EBF3ED"

CABECERA = '''digraph {
  rankdir=%s;
  bgcolor="transparent";
  node [fontname="Helvetica", fontsize=10, shape=box, style="rounded,filled",
        penwidth=1.4, margin="0.16,0.10"];
  edge [fontname="Helvetica", fontsize=9, color="#555555", penwidth=1.1,
        arrowsize=0.8];
'''


def render(nombre, cuerpo, rankdir="TB"):
    if not shutil.which("dot"):
        print("  [ERROR] falta Graphviz: no se encuentra el ejecutable dot")
        return
    DESTINO.mkdir(parents=True, exist_ok=True)
    dot = CABECERA % rankdir + cuerpo + "\n}\n"
    (DESTINO / f"{nombre}.dot").write_text(dot, encoding="utf-8")
    salida = DESTINO / f"{nombre}.png"
    subprocess.run(["dot", "-Tpng", "-Gdpi=200", "-o", str(salida)],
                   input=dot, text=True, check=True)
    print(f"  {salida.name}")


def diag_arquitectura():
    """Las dos capas y el recorrido completo de un turno."""
    render("diag_arquitectura", f'''
  subgraph cluster_datos {{
    label="Datos"; fontname="Helvetica"; fontsize=10; fontcolor="{GRIS}";
    color="{GRIS}"; style=dashed; penwidth=1;
    turno [label="Turno de 4 h\\n32.791 transacciones", color="{GRIS}", fillcolor="{GRIS_F}"];
  }}

  subgraph cluster_c1 {{
    label="Capa 1 — Detector  (determinista)"; fontname="Helvetica";
    fontsize=10; fontcolor="{AZUL}"; color="{AZUL}"; style=dashed; penwidth=1.2;
    punt [label="XGBoost\\npuntúa cada transacción", color="{AZUL}", fillcolor="{AZUL_F}"];
    shap [label="Contribuciones\\npor variable (SHAP)", color="{AZUL}", fillcolor="{AZUL_F}"];
    sel  [label="Selección por umbral\\ny capacidad de revisión", color="{AZUL}", fillcolor="{AZUL_F}"];
  }}

  exp [label="EXPEDIENTE\\n55 casos elevados", shape=note, color="{GRIS}", fillcolor="{GRIS_F}"];

  subgraph cluster_c2 {{
    label="Capa 2 — Departamento  (estocástica)"; fontname="Helvetica";
    fontsize=10; fontcolor="{ROJO}"; color="{ROJO}"; style=dashed; penwidth=1.2;
    mod [label="Modelador\\npresenta los casos", color="{ROJO}", fillcolor="{ROJO_F}"];
    inv [label="Investigador\\nexplica y emite veredicto", color="{ROJO}", fillcolor="{ROJO_F}"];
    rep [label="Reportero\\nredacta el informe", color="{ROJO}", fillcolor="{ROJO_F}"];
  }}

  tabla [label="Tabla de casos\\nensamblada sin modelo", color="{AZUL}", fillcolor="{AZUL_F}"];
  inf   [label="INFORME", shape=note, color="{GRIS}", fillcolor="{GRIS_F}"];
  aud   [label="Auditor\\ncobertura, invenciones, idioma", color="{VERDE}", fillcolor="{VERDE_F}"];
  fin   [label="FIABLE  /  NO FIABLE", shape=box, color="{VERDE}", fillcolor="{VERDE_F}"];

  turno -> punt -> shap -> sel -> exp;
  exp -> mod -> inv -> rep;
  inv -> tabla [label="veredictos", style=dashed];
  tabla -> rep [style=dashed];
  rep -> inf -> aud -> fin;
''')


def diag_caso():
    """El recorrido de un caso individual, y donde se separa prosa de veredicto."""
    render("diag_caso", f'''
  tx   [label="Transacción\\nV1–V28, importe, hora", color="{GRIS}", fillcolor="{GRIS_F}"];
  prob [label="Probabilidad de fraude", color="{AZUL}", fillcolor="{AZUL_F}"];
  contr[label="Contribuciones por variable", color="{AZUL}", fillcolor="{AZUL_F}"];
  niv  [label="Nivel de riesgo\\n(etiqueta derivada del umbral)", color="{AZUL}", fillcolor="{AZUL_F}"];
  dos  [label="DOSSIER DEL CASO", shape=note, color="{GRIS}", fillcolor="{GRIS_F}"];

  llm  [label="Investigador\\n(modelo de lenguaje)", color="{ROJO}", fillcolor="{ROJO_F}", penwidth=2];
  pros [label="Párrafo explicativo", color="{ROJO}", fillcolor="{ROJO_F}"];
  ver  [label="VEREDICTO\\nconfirmado / descartado", color="{ROJO}", fillcolor="{ROJO_F}"];

  met  [label="Métricas del sistema", color="{VERDE}", fillcolor="{VERDE_F}"];
  txt  [label="Texto del informe", color="{GRIS}", fillcolor="{GRIS_F}"];

  tx -> prob; tx -> contr; prob -> niv;
  prob -> dos; contr -> dos; niv -> dos [label="  se retira en\\n  la ablación", fontcolor="{GRIS}", style=dashed];
  dos -> llm;
  llm -> pros; llm -> ver;
  pros -> txt;
  ver -> met;

  {{ rank=same; pros; ver; }}
  pros -> ver [label="  no se corresponden\\n  (sección 5.12)", color="{ROJO}",
               style=dotted, penwidth=1.6, fontcolor="{ROJO}", dir=both,
               arrowhead=none, arrowtail=none];
''', rankdir="TB")


def diag_experimentos():
    """Mapa del diseno experimental: que se compara contra que."""
    render("diag_experimentos", f'''
  ds [label="Conjunto ULB\\n284.807 transacciones", color="{GRIS}", fillcolor="{GRIS_F}"];

  subgraph cluster_part {{
    label="Particiones"; fontname="Helvetica"; fontsize=10; fontcolor="{GRIS}";
    color="{GRIS}"; style=dashed;
    alea [label="Aleatoria\\nestratificada", color="{AZUL}", fillcolor="{AZUL_F}"];
    temp [label="Temporal\\npasado → futuro", color="{AZUL}", fillcolor="{AZUL_F}"];
  }}

  subgraph cluster_c1 {{
    label="Experimentos sobre la capa 1"; fontname="Helvetica"; fontsize=10;
    fontcolor="{AZUL}"; color="{AZUL}"; style=dashed;
    e1 [label="Comparación de detectores\\nXGBoost · RF · Isolation Forest", color="{AZUL}", fillcolor="{AZUL_F}"];
    e2 [label="Ablación del desbalanceo\\n4 estrategias", color="{AZUL}", fillcolor="{AZUL_F}"];
    e3 [label="Ablación de variables\\n4 grupos", color="{AZUL}", fillcolor="{AZUL_F}"];
  }}

  turnos [label="4 turnos de 4 h\\npor desplazamiento del inicio", color="{GRIS}", fillcolor="{GRIS_F}"];

  subgraph cluster_c2 {{
    label="Experimentos sobre la capa 2"; fontname="Helvetica"; fontsize=10;
    fontcolor="{ROJO}"; color="{ROJO}"; style=dashed;
    e4 [label="Comparativa de modelos\\n3 modelos × 16 ejecuciones", color="{ROJO}", fillcolor="{ROJO_F}"];
    e5 [label="Ablación del expediente\\n3 niveles × 48 ejecuciones", color="{ROJO}", fillcolor="{ROJO_F}"];
    e6 [label="Corrección de dominio\\n2 condiciones × 192 veredictos", color="{ROJO}", fillcolor="{ROJO_F}"];
    e7 [label="Modelo de mayor capacidad\\n72B por descomposición en capas", color="{ROJO}", fillcolor="{ROJO_F}"];
    e8 [label="Operación en continuo\\nventanas de 5 a 240 min", color="{ROJO}", fillcolor="{ROJO_F}"];
  }}

  base [label="LÍNEA BASE\\nel detector sin capa 2", shape=box, color="{VERDE}",
        fillcolor="{VERDE_F}", penwidth=2];

  ds -> alea; ds -> temp;
  alea -> e1; temp -> e1; alea -> e2; temp -> e3;
  temp -> turnos;
  turnos -> e4; turnos -> e5; turnos -> e6; turnos -> e7; turnos -> e8;
  e1 -> base [style=invis];
  base -> e4 [label="  se compara contra", color="{VERDE}", fontcolor="{VERDE}", penwidth=1.6];
  base -> e5 [color="{VERDE}", penwidth=1.6];
  base -> e6 [color="{VERDE}", penwidth=1.6];
''', rankdir="TB")


DIAGRAMAS = [diag_arquitectura, diag_caso, diag_experimentos]


def main():
    print("=" * 60)
    print("  DIAGRAMAS DE LA MEMORIA")
    print("=" * 60)
    for d in DIAGRAMAS:
        try:
            d()
        except Exception as e:
            print(f"  [ERROR] {d.__name__}: {type(e).__name__}: {e}")
    print(f"\n  Destino: {DESTINO}")
    print("  Se guarda tambien el .dot de cada uno, por si hay que retocarlo.")


if __name__ == "__main__":
    main()
