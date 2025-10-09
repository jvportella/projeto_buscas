import os
import sys
import time
import threading
from math import log2
import random

import pygame
import chess

# ------------------------------------------------------------
# (Opcional) Ajuste automático do PATH do Graphviz no Windows
#   • Se você instalou o Graphviz em outro caminho, troque abaixo.
#   • Se já funciona `dot -V` no PowerShell, você pode remover isto.
# ------------------------------------------------------------
if os.name == "nt":
    default_gv = r"C:\Program Files\Graphviz\bin"
    if os.path.isdir(default_gv) and default_gv not in os.environ.get("PATH", ""):
        os.environ["PATH"] += os.pathsep + default_gv

# ------------------------------------------------------------
# Import do graphviz com sinalização de disponibilidade
# ------------------------------------------------------------
try:
    from graphviz import Digraph
    GRAPHVIZ_AVAILABLE = True
except Exception:
    GRAPHVIZ_AVAILABLE = False

# ===================================================
# Classe que representa cada nó da Árvore de Decisão
# ===================================================
class DecisionNode:
    def __init__(self, question=None, true_branch=None, false_branch=None, action=None, name=None):
        self.question = question
        self.true_branch = true_branch
        self.false_branch = false_branch
        self.action = action
        self.name = name or (question.__name__ if question else (action.__name__ if action else 'Node'))

    def evaluate(self, board, path=None, nodes=None):
        # Percorre a árvore e retorna o movimento e o caminho percorrido
        if path is None:
            path = []
        if nodes is None:
            nodes = []
        nodes.append(self)
        if self.action:
            path.append(f"Ação: {self.name}")
            return self.action(board), path, nodes
        else:
            try:
                result = bool(self.question(board))
            except Exception:
                result = False
            path.append(f"Pergunta: {self.name} -> {result}")
            next_branch = self.true_branch if result else self.false_branch
            return next_branch.evaluate(board, path, nodes)

# ===================================================
# Funções de decisão (condições e ações da IA)
# ===================================================
def is_king_in_danger(board):
    return board.is_check()

def can_capture(board):
    return any(board.is_capture(m) for m in board.legal_moves)

def can_develop_piece(board):
    rank = 0 if board.turn == chess.WHITE else 7
    for f in range(8):
        sq = chess.square(f, rank)
        p = board.piece_at(sq)
        if p and p.color == board.turn and p.piece_type in (chess.KNIGHT, chess.BISHOP):
            return True
    return False

def move_king(board):
    moves = [m for m in board.legal_moves if board.piece_at(m.from_square).piece_type == chess.KING]
    return random.choice(moves) if moves else random.choice(list(board.legal_moves))

def capture_move(board):
    moves = [m for m in board.legal_moves if board.is_capture(m)]
    return random.choice(moves) if moves else random.choice(list(board.legal_moves))

def develop_move(board):
    moves = [m for m in board.legal_moves if board.piece_at(m.from_square)
             and board.piece_at(m.from_square).piece_type in (chess.KNIGHT, chess.BISHOP)
             and board.piece_at(m.from_square).color == board.turn]
    return random.choice(moves) if moves else random.choice(list(board.legal_moves))

def random_move(board):
    return random.choice(list(board.legal_moves))

def build_decision_tree():
    return DecisionNode(
        question=is_king_in_danger,
        name='is_king_in_danger',
        true_branch=DecisionNode(action=move_king, name='move_king'),
        false_branch=DecisionNode(
            question=can_capture,
            name='can_capture',
            true_branch=DecisionNode(action=capture_move, name='capture_move'),
            false_branch=DecisionNode(
                question=can_develop_piece,
                name='can_develop_piece',
                true_branch=DecisionNode(action=develop_move, name='develop_move'),
                false_branch=DecisionNode(action=random_move, name='random_move')
            )
        )
    )

# ===================================================
# Heurísticas rápidas para dados reais no gráfico
# ===================================================
def calc_entropy(board):
    n = len(list(board.legal_moves)) or 1
    return round(log2(n), 2)

def calc_value(board):
    values = {chess.PAWN:1, chess.KNIGHT:3, chess.BISHOP:3, chess.ROOK:5, chess.QUEEN:9}
    total = 0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p:
            val = values.get(p.piece_type, 0)
            total += val if p.color == chess.WHITE else -val
    return round(total, 2)

def calc_samples(board):
    return len(list(board.legal_moves))

def calc_class(board):
    if board.is_check():
        return 0
    if any(board.is_capture(m) for m in board.legal_moves):
        return 1
    return 0

# ===================================================
# Export visual da Árvore (corrigido: sem PermissionError)
# ===================================================
USE_THREADS = True  # mude para False se quiser export síncrono (útil para depurar)

def export_tree_graph(root, visited_nodes=None, filename="tree", board=None):
    """
    Gera PNG da árvore em graphs/<filename>_<timestamp>.png
    Evita PermissionError por conflito com 'tree' (arquivo/pasta).
    Tolera ausência do Graphviz do sistema (apenas loga aviso).
    """
    if not GRAPHVIZ_AVAILABLE:
        print("[graphviz] pacote Python indisponível; instale com: pip install graphviz")
        return

    # garante diretório de saída
    out_dir = "graphs"
    os.makedirs(out_dir, exist_ok=True)

    # nome único para evitar colisão com 'tree' existente
    ts = time.strftime("%Y%m%d-%H%M%S")
    safe_name = f"{filename}_{ts}"

    try:
        dot = Digraph(name='DecisionTree', format='png')
        dot.attr(rankdir='TB', bgcolor='white')
        visited_ids = set(id(n) for n in (visited_nodes or []))

        def add_node(node):
            nid = str(id(node))
            entropy = calc_entropy(board) if board else 0.0
            samples = calc_samples(board) if board else 0
            value = calc_value(board) if board else 0.0
            cls = calc_class(board) if board else 0

            label = f"{node.name}\nentropy = {entropy}\nsamples = {samples}\nvalue = {value}\nclass = {cls}"

            if node.action:
                color = 'orange' if id(node) in visited_ids else 'lightgrey'
                dot.node(nid, label=label, style='filled', fillcolor=color, shape='box')
            else:
                color = 'skyblue' if id(node) in visited_ids else 'white'
                dot.node(nid, label=label, style='filled', fillcolor=color, shape='ellipse')

            if node.true_branch:
                add_node(node.true_branch)
                dot.edge(nid, str(id(node.true_branch)), label='True')
            if node.false_branch:
                add_node(node.false_branch)
                dot.edge(nid, str(id(node.false_branch)), label='False')

        add_node(root)

        # render no diretório de saída
        result = dot.render(filename=safe_name, directory=out_dir, cleanup=True)
        print(f"[graphviz] salvo: {result}")
    except FileNotFoundError as e:
        # dot.exe não encontrado
        print("[graphviz] 'dot' não encontrado. Instale o Graphviz do sistema e/ou deixe no PATH.")
        print("  Windows (PowerShell): winget install Graphviz.Graphviz ; depois reinicie o VS Code")
        print("  Ou ajuste o caminho no topo do script (PATH do Graphviz).")
        print(f"  Detalhe: {e}")
    except PermissionError as e:
        # conflito de nome/arquivo bloqueado
        print("[graphviz] Permissão negada ao salvar. Verifique se existe um arquivo ou pasta chamada 'tree' na raiz.")
        print("  Agora salvamos com timestamp em 'graphs/' para evitar colisão, mas confira permissões.")
        print(f"  Detalhe: {e}")
    except Exception as e:
        print(f"[graphviz] falhou ao renderizar: {e}")

# ===================================================
# Pygame UI
# ===================================================
pygame.init()
WIDTH, HEIGHT = 640, 640
SQUARE = WIDTH // 8
FPS = 60
FONT = pygame.font.SysFont("Segoe UI Symbol", 36)
SMALL = pygame.font.SysFont("Arial", 16)
UNICODE = {'P':'♙','N':'♘','B':'♗','R':'♖','Q':'♕','K':'♔','p':'♟','n':'♞','b':'♝','r':'♜','q':'♛','k':'♚'}

WIN = pygame.display.set_mode((WIDTH, HEIGHT + 120))
pygame.display.set_caption("Xadrez com IA - Árvore de Decisão (robusta)")
clock = pygame.time.Clock()

def rc_to_square(r, c):
    return chess.square(c, 7 - r)

def square_to_rc(sq):
    return (7 - chess.square_rank(sq), chess.square_file(sq))

def draw(board, selected, legal_moves):
    colors = [(240,217,181),(181,136,99)]
    for r in range(8):
        for c in range(8):
            rect = pygame.Rect(c*SQUARE, r*SQUARE, SQUARE, SQUARE)
            pygame.draw.rect(WIN, colors[(r+c)%2], rect)
    for m in legal_moves:
        tr, tc = square_to_rc(m.to_square)
        pygame.draw.circle(WIN, (50,200,50), (tc*SQUARE+SQUARE//2, tr*SQUARE+SQUARE//2), 10)
    if selected is not None:
        sr, sc = square_to_rc(selected)
        pygame.draw.rect(WIN, (102,205,170), pygame.Rect(sc*SQUARE, sr*SQUARE, SQUARE, SQUARE), 4)
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p:
            r, c = square_to_rc(sq)
            WIN.blit(FONT.render(UNICODE[p.symbol()], True, (0,0,0)), (c*SQUARE+10, r*SQUARE+5))
    pygame.draw.rect(WIN, (40,40,40), (0, HEIGHT, WIDTH, 120))
    WIN.blit(SMALL.render("Pressione T para gerar a árvore (salva em graphs/)", True, (255,255,255)), (8, HEIGHT+8))
    pygame.display.flip()

def animate_move(board, move):
    piece = board.piece_at(move.from_square)
    if not piece: return
    glyph = FONT.render(UNICODE[piece.symbol()], True, (0,0,0))
    sr, sc = square_to_rc(move.from_square)
    tr, tc = square_to_rc(move.to_square)
    for i in range(1, 13):
        draw(board, None, [])
        x = sc*SQUARE + (tc-sc)*SQUARE*i/12
        y = sr*SQUARE + (tr-sr)*SQUARE*i/12
        WIN.blit(glyph, (x+SQUARE//4, y+SQUARE//4))
        pygame.display.flip()
        clock.tick(FPS)

def main():
    board = chess.Board()
    tree = build_decision_tree()
    selected = None
    legal = []

    running = True
    while running:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_t:
                move, path, visited = tree.evaluate(board)
                # export (thread ou síncrono)
                if USE_THREADS:
                    threading.Thread(
                        target=export_tree_graph,
                        args=(tree,),
                        kwargs={"visited_nodes": visited, "filename": "tree", "board": board},
                        daemon=True
                    ).start()
                else:
                    export_tree_graph(tree, visited_nodes=visited, filename="tree", board=board)
            elif e.type == pygame.MOUSEBUTTONDOWN and board.turn == chess.WHITE:
                mx,my = pygame.mouse.get_pos()
                if my < HEIGHT:
                    c,r = mx//SQUARE, my//SQUARE
                    sq = rc_to_square(r,c)
                    piece = board.piece_at(sq)
                    if selected is None:
                        if piece and piece.color == chess.WHITE:
                            selected = sq
                            legal = [m for m in board.legal_moves if m.from_square == sq]
                    else:
                        move = chess.Move(selected, sq)
                        if chess.square_rank(sq)==7 and board.piece_at(selected) and board.piece_at(selected).piece_type==chess.PAWN:
                            move = chess.Move(selected, sq, promotion=chess.QUEEN)
                        if move in board.legal_moves:
                            animate_move(board, move)
                            board.push(move)
                            selected, legal = None, []
                        else:
                            selected, legal = None, []

        # Movimento da IA (pretas)
        if board.turn == chess.BLACK and not board.is_game_over():
            move, path, visited = tree.evaluate(board)
            animate_move(board, move)
            board.push(move)
            if USE_THREADS:
                threading.Thread(
                    target=export_tree_graph,
                    args=(tree,),
                    kwargs={"visited_nodes": visited, "filename": "tree", "board": board},
                    daemon=True
                ).start()
            else:
                export_tree_graph(tree, visited_nodes=visited, filename="tree", board=board)

        draw(board, selected, legal)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
