import pygame, random, joblib
import numpy as np

# Inicialização
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🚀 Space IA – Nave x Boss")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 22, bold=True)

# Carregar modelo IA
clf = joblib.load("ai_model.pkl")

# Cores
WHITE = (255, 255, 255)
RED = (255, 60, 60)
GREEN = (50, 255, 50)
BLUE = (80, 150, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 220, 80)

# Objetos
class Nave:
    def __init__(self):
        self.rect = pygame.Rect(WIDTH//2 - 25, HEIGHT - 80, 50, 50)
        self.vel = 6
        self.shots = []
        self.life = 5
        self.ai_enabled = False
        self.decision = "Manual"

    def move(self, keys):
        if keys[pygame.K_LEFT] and self.rect.left > 0: self.rect.x -= self.vel
        if keys[pygame.K_RIGHT] and self.rect.right < WIDTH: self.rect.x += self.vel
        if keys[pygame.K_UP] and self.rect.top > 0: self.rect.y -= self.vel
        if keys[pygame.K_DOWN] and self.rect.bottom < HEIGHT: self.rect.y += self.vel

    def shoot(self):
        self.shots.append(pygame.Rect(self.rect.centerx - 3, self.rect.top - 10, 6, 12))

    def update_shots(self):
        for s in self.shots[:]:
            s.y -= 10
            if s.bottom < 0:
                self.shots.remove(s)

    def draw(self):
        pygame.draw.rect(screen, BLUE, self.rect)
        for s in self.shots:
            pygame.draw.rect(screen, YELLOW, s)


class Boss:
    def __init__(self):
        self.rect = pygame.Rect(WIDTH//2 - 50, 40, 100, 60)
        self.shots = []
        self.cooldown = 0
        self.life = 15

    def shoot(self):
        if self.cooldown <= 0:
            self.shots.append(pygame.Rect(self.rect.centerx - 5, self.rect.bottom, 10, 20))
            self.cooldown = 40
        else:
            self.cooldown -= 1

    def update_shots(self):
        for s in self.shots[:]:
            s.y += 7
            if s.top > HEIGHT:
                self.shots.remove(s)

    def draw(self):
        pygame.draw.rect(screen, RED, self.rect)
        for s in self.shots:
            pygame.draw.rect(screen, (255, 150, 150), s)


# Função IA para decidir movimentos
def ia_decision(nave, boss):
    if not boss.shots: 
        return 4  # atirar se não houver projéteis

    # pegar projétil mais próximo
    proj = min(boss.shots, key=lambda p: abs(p.x - nave.rect.x) + abs(p.y - nave.rect.y))
    dist_x = proj.x - nave.rect.x
    dist_y = proj.y - nave.rect.y

    action = clf.predict([[dist_x, dist_y]])[0]
    return int(action)

# Botão IA
ia_button = pygame.Rect(WIDTH - 200, 20, 160, 40)

# Inicializar entidades
nave = Nave()
boss = Boss()

# Loop principal
running = True
while running:
    clock.tick(60)
    screen.fill((10, 10, 30))
    keys = pygame.key.get_pressed()

    # Eventos
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        if e.type == pygame.MOUSEBUTTONDOWN:
            if ia_button.collidepoint(e.pos):
                nave.ai_enabled = not nave.ai_enabled
                nave.decision = "IA Ativada" if nave.ai_enabled else "Manual"
        if e.type == pygame.KEYDOWN and not nave.ai_enabled:
            if e.key == pygame.K_SPACE:
                nave.shoot()

    # Atualizações
    if nave.ai_enabled:
        action = ia_decision(nave, boss)
        nave.decision = ["←", "→", "↑", "↓", "Atirar"][action]
        if action == 0 and nave.rect.left > 0: nave.rect.x -= nave.vel
        if action == 1 and nave.rect.right < WIDTH: nave.rect.x += nave.vel
        if action == 2 and nave.rect.top > 0: nave.rect.y -= nave.vel
        if action == 3 and nave.rect.bottom < HEIGHT: nave.rect.y += nave.vel
        if action == 4: nave.shoot()
    else:
        nave.move(keys)

    nave.update_shots()
    boss.update_shots()
    boss.shoot()

    # Colisões
    for shot in nave.shots[:]:
        if shot.colliderect(boss.rect):
            nave.shots.remove(shot)
            boss.life -= 1

    for shot in boss.shots[:]:
        if shot.colliderect(nave.rect):
            boss.shots.remove(shot)
            nave.life -= 1

    # Game Over ou Vitória
    if nave.life <= 0:
        msg = font.render("💀 GAME OVER!", True, RED)
        screen.blit(msg, (WIDTH//2 - 100, HEIGHT//2))
        pygame.display.flip()
        pygame.time.wait(2000)
        running = False
    if boss.life <= 0:
        msg = font.render("🏆 VITÓRIA!", True, GREEN)
        screen.blit(msg, (WIDTH//2 - 80, HEIGHT//2))
        pygame.display.flip()
        pygame.time.wait(2000)
        running = False

    # Desenhar
    nave.draw()
    boss.draw()

    # HUD
    pygame.draw.rect(screen, (60, 60, 60), ia_button)
    txt = font.render("Ativar IA" if not nave.ai_enabled else "Desativar IA", True, WHITE)
    screen.blit(txt, (ia_button.x + 15, ia_button.y + 8))
    status = font.render(f"Modo: {nave.decision}", True, WHITE)
    screen.blit(status, (20, 20))
    stats = font.render(f"Vida Nave: {nave.life} | Vida Boss: {boss.life}", True, YELLOW)
    screen.blit(stats, (20, 50))

    pygame.display.flip()

pygame.quit()
