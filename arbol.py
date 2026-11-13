"""Árbol de derivación: cada nodo interno es un no terminal y sus hijos son el
lado derecho de la producción que se aplicó; las hojas son tokens o ε.
"""
from .gramatica import es_no_terminal, mostrar, EPSILON


class Nodo:
    def __init__(self, simbolo):
        self.simbolo = simbolo
        self.hijos = []
        self.token = None          # solo en hojas terminales que sí se leyeron
        self.produccion = None     # solo en no terminales expandidos
        self.falta = False         # terminal o no terminal que no se pudo completar por un error

    @property
    def es_epsilon(self):
        return self.simbolo == EPSILON

    def hojas(self):
        """Tokens de las hojas leídos de izquierda a derecha (la frontera del árbol)."""
        if self.token is not None:
            return [self.token]
        return [t for h in self.hijos for t in h.hojas()]

    def etiqueta(self):
        if self.es_epsilon:
            return EPSILON
        if es_no_terminal(self.simbolo):
            return self.simbolo + ('  ✗ incompleto' if self.falta else '')
        if self.token is None:
            return f'{mostrar(self.simbolo)}  ✗ faltante'
        t = self.token
        posicion = f'[{t.fila}:{t.columna}]'
        if t.terminal == t.lexema:                # literal: "si", "{", "==" ...
            return f'"{t.lexema}"  {posicion}'
        return f'{t.categoria}: {t.lexema}  {posicion}'


def a_texto(raiz, con_epsilon=True):
    """Dibuja el árbol con líneas, un nodo por renglón."""
    lineas = [raiz.etiqueta()]

    def recorrer(nodo, prefijo):
        hijos = [h for h in nodo.hijos if con_epsilon or not h.es_epsilon]
        for k, hijo in enumerate(hijos):
            ultimo = k == len(hijos) - 1
            lineas.append(prefijo + ('└── ' if ultimo else '├── ') + hijo.etiqueta())
            recorrer(hijo, prefijo + ('    ' if ultimo else '│   '))

    recorrer(raiz, '')
    return '\n'.join(lineas)


def a_dot(raiz, con_epsilon=True):
    """El árbol en formato Graphviz (dot -Tpng arbol.dot -o arbol.png)."""
    lineas = ['digraph arbol {', '  ordering=out;',
              '  node [shape=box, style="rounded,filled", fillcolor="#eef2f8", fontname="Helvetica"];',
              '  edge [arrowhead=none];']
    contador = [0]

    def escapar(texto):
        return texto.replace('\\', '\\\\').replace('"', '\\"')

    def visitar(nodo):
        contador[0] += 1
        nombre = f'n{contador[0]}'
        relleno = '#eef2f8' if es_no_terminal(nodo.simbolo) else '#dcfce7'
        if nodo.falta or (not es_no_terminal(nodo.simbolo) and nodo.token is None and not nodo.es_epsilon):
            relleno = '#fecaca'
        forma = ', shape=plaintext, style=""' if nodo.es_epsilon else f', fillcolor="{relleno}"'
        lineas.append(f'  {nombre} [label="{escapar(nodo.etiqueta())}"{forma}];')
        for hijo in nodo.hijos:
            if con_epsilon or not hijo.es_epsilon:
                lineas.append(f'  {nombre} -> {visitar(hijo)};')
        return nombre

    visitar(raiz)
    lineas.append('}')
    return '\n'.join(lineas)
