"""Árbol sintáctico abstracto (AST), opcional: python main.py archivo.iron --ast

El árbol de derivación de G tiene la forma que le dio la eliminación de la
recursividad por la izquierda: en  a - b - c  la segunda resta queda dentro de
<arit_cola>, anidada a la derecha. Si se evaluara así, 10 - 3 - 2 daría 9.
El AST recorre cada no terminal con cola (<expr>, <conj>, <arit>, <term>) y
pliega los operandos de izquierda a derecha: ((10 - 3) - 2) = 5. Las
expresiones se escriben con todos los paréntesis para que se vea la
precedencia y la asociatividad que impone la gramática.

Este módulo sí conoce los nombres de los no terminales de G, porque traduce
cada uno a su significado. El parser no depende de él.
"""
from .arbol import Nodo

CON_COLA = ('<expr>', '<conj>', '<arit>', '<term>')   # X ::= <siguiente_nivel> <X_cola>


def _es_vacio(nodo):
    return nodo.hijos[0].es_epsilon


def _operador(nodo):
    """El lexema del operador: el nodo es un terminal ("o", "y") o <oprel>/<opsuma>/<opmul>."""
    return nodo.token.lexema if nodo.token else nodo.hijos[0].token.lexema


def expresion(n):
    """Convierte el subárbol de una expresión en texto con paréntesis explícitos."""
    s, h = n.simbolo, n.hijos
    if s in CON_COLA:
        valor, cola = expresion(h[0]), h[1]
        while not _es_vacio(cola):               # cola ::= op <siguiente> cola | ε
            valor = f'({valor} {_operador(cola.hijos[0])} {expresion(cola.hijos[1])})'
            cola = cola.hijos[2]
        return valor
    if s == '<neg>':
        return f'(no {expresion(h[1])})' if h[0].simbolo == 'no' else expresion(h[0])
    if s == '<rel>':
        izquierda, cola = expresion(h[0]), h[1]
        if _es_vacio(cola):
            return izquierda
        return f'({izquierda} {_operador(cola.hijos[0])} {expresion(cola.hijos[1])})'
    if s == '<unario>':
        return f'(-{expresion(h[1])})' if h[0].simbolo == '-' else expresion(h[0])
    if s == '<prim>':
        return expresion(h[1]) if h[0].simbolo == '(' else h[0].token.lexema
    raise ValueError(f'{s} no es parte de una expresión')


def _sentencias(bloque):
    """<bloque> ::= "{" <sentencias> "}" ; <sentencias> ::= <sentencia> <sentencias> | ε"""
    lista, s = [], bloque.hijos[1]
    while not _es_vacio(s):
        lista.append(_sentencia(s.hijos[0]))
        s = s.hijos[1]
    return lista


def _sentencia(n):
    h = n.hijos
    primero = h[0].simbolo
    if primero == 'var':
        return (f'var {h[1].token.lexema} = {expresion(h[3])}', [])
    if primero == 'ID':
        return (f'{h[0].token.lexema} = {expresion(h[2])}', [])
    if primero == 'serie':
        carga = h[3]
        texto = f'serie {h[1].token.lexema} {h[2].token.lexema}'
        if not _es_vacio(carga):
            texto += f' con {expresion(carga.hijos[1])}'
        return (texto, [])
    if primero == 'descanso':
        return (f'descanso {expresion(h[1])}', [])
    if primero == 'si':
        hijos = [('entonces', _sentencias(h[4]))]
        if not _es_vacio(h[5]):
            hijos.append(('sino', _sentencias(h[5].hijos[1])))
        return (f'si {expresion(h[2])}', hijos)
    if primero == 'repetir':
        return (f'repetir {expresion(h[1])} veces', _sentencias(h[2]))
    # Una sentencia agregada a la gramática después: se muestran sus tokens tal cual.
    return (' '.join(t.lexema for t in n.hojas()), [])


def construir(raiz: Nodo):
    """Devuelve el AST como (etiqueta, [hijos]) a partir del árbol de derivación."""
    rutinas, n = [raiz.hijos[0]], raiz.hijos[1]
    while not _es_vacio(n):                      # <mas_rutinas> ::= <rutina> <mas_rutinas> | ε
        rutinas.append(n.hijos[0])
        n = n.hijos[1]
    return ('programa', [(f'rutina {r.hijos[1].token.lexema}', _sentencias(r.hijos[2]))
                         for r in rutinas])


def a_texto(ast):
    etiqueta, hijos = ast
    lineas = [etiqueta]

    def recorrer(hijos, prefijo):
        for k, (texto, nietos) in enumerate(hijos):
            ultimo = k == len(hijos) - 1
            lineas.append(prefijo + ('└── ' if ultimo else '├── ') + texto)
            recorrer(nietos, prefijo + ('    ' if ultimo else '│   '))

    recorrer(hijos, '')
    return '\n'.join(lineas)
