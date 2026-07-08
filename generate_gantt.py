import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
import numpy as np

# Définir les dates du projet (6 mois)
start_date = datetime(2026, 5, 9)  # Date actuelle
end_date = start_date + timedelta(days=180)  # 6 mois = ~180 jours

# Définir les phases et tâches du projet
tasks = [
    {"name": "Phase 1: Planification et Setup", "start": 0, "duration": 15, "color": "#FF6B6B"},
    {"name": "  - Planification du projet", "start": 0, "duration": 5, "color": "#FFB3B3"},
    {"name": "  - Setup infrastructure", "start": 5, "duration": 10, "color": "#FFB3B3"},
    
    {"name": "Phase 2: Développement Backend", "start": 15, "duration": 45, "color": "#4ECDC4"},
    {"name": "  - API et endpoints", "start": 15, "duration": 15, "color": "#95E1D3"},
    {"name": "  - Services IA et agents", "start": 30, "duration": 20, "color": "#95E1D3"},
    {"name": "  - Base de données", "start": 15, "duration": 25, "color": "#95E1D3"},
    
    {"name": "Phase 3: Développement Frontend", "start": 20, "duration": 40, "color": "#45B7D1"},
    {"name": "  - UI/UX design", "start": 20, "duration": 10, "color": "#90D8F0"},
    {"name": "  - Composants Angular", "start": 30, "duration": 25, "color": "#90D8F0"},
    {"name": "  - Intégration API", "start": 55, "duration": 5, "color": "#90D8F0"},
    
    {"name": "Phase 4: Intégration et Tests", "start": 55, "duration": 35, "color": "#F7DC6F"},
    {"name": "  - Tests unitaires", "start": 55, "duration": 10, "color": "#F9E79F"},
    {"name": "  - Tests d'intégration", "start": 65, "duration": 10, "color": "#F9E79F"},
    {"name": "  - Optimisation performance", "start": 75, "duration": 15, "color": "#F9E79F"},
    
    {"name": "Phase 5: Déploiement", "start": 85, "duration": 20, "color": "#BB8FCE"},
    {"name": "  - Configuration prod", "start": 85, "duration": 5, "color": "#D7BDE2"},
    {"name": "  - Déploiement", "start": 90, "duration": 5, "color": "#D7BDE2"},
    {"name": "  - Support et monitoring", "start": 95, "duration": 10, "color": "#D7BDE2"},
]

# Créer la figure
fig, ax = plt.subplots(figsize=(16, 10))

# Couleurs
colors = []
y_labels = []
y_pos = []

for idx, task in enumerate(tasks):
    colors.append(task["color"])
    y_labels.append(task["name"])
    y_pos.append(idx)
    
    # Dessiner la barre de tâche
    ax.barh(idx, task["duration"], left=task["start"], height=0.6, 
            color=task["color"], edgecolor='black', linewidth=0.5, alpha=0.8)
    
    # Ajouter le label avec la durée
    if task["duration"] > 3:  # Seulement si la barre est assez grande
        mid_point = task["start"] + task["duration"] / 2
        ax.text(mid_point, idx, f'{task["duration"]}j', 
               va='center', ha='center', fontsize=8, fontweight='bold', color='white')

# Configuration du graphique
ax.set_yticks(y_pos)
ax.set_yticklabels(y_labels, fontsize=9)
ax.set_xlabel('Jours du projet', fontsize=11, fontweight='bold')
ax.set_title('Diagramme de Gantt - Projet PIQBIT (6 mois)', fontsize=14, fontweight='bold', pad=20)

# Ajouter une grille
ax.grid(True, axis='x', alpha=0.3, linestyle='--')
ax.set_axisbelow(True)

# Définir les limites
ax.set_xlim(0, 180)

# Ajouter des marqueurs pour les mois
month_marks = [0, 30, 60, 90, 120, 150, 180]
month_labels = ['Jour 0', 'Mois 1', 'Mois 2', 'Mois 3', 'Mois 4', 'Mois 5', 'Mois 6']
ax.set_xticks(month_marks)
ax.set_xticklabels(month_labels, fontsize=9)

# Ajouter des lignes verticales pour les mois
for mark in month_marks[1:]:
    ax.axvline(x=mark, color='gray', linestyle=':', alpha=0.5, linewidth=1)

# Ajuster les marges
plt.tight_layout()

# Sauvegarder en PNG
output_path = r'e:\PIQBIT\gantt_diagram.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✓ Diagramme de Gantt généré avec succès: {output_path}")

# Afficher les statistiques
print("\n" + "="*50)
print("STATISTIQUES DU PROJET")
print("="*50)
print(f"Date de début: {start_date.strftime('%d-%m-%Y')}")
print(f"Date de fin: {end_date.strftime('%d-%m-%Y')}")
print(f"Durée totale: 6 mois (180 jours)")
print("\nPhases du projet:")
print("  1. Planification et Setup: 15 jours")
print("  2. Développement Backend: 45 jours")
print("  3. Développement Frontend: 40 jours")
print("  4. Intégration et Tests: 35 jours")
print("  5. Déploiement: 20 jours")
print("="*50)

plt.show()
