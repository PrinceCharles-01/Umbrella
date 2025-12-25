# 🐛 Notes de Bugs & Corrections - Umbrella PharmFinder

Documentation des bugs rencontrés et leurs solutions pour référence future.

---

## 📅 Décembre 2024

### Bug #1: Modales instables / "Pop-ups dansantes"

**Date**: 25 décembre 2024

**Symptômes**:
- Les pop-ups/modales (Dialog, Sheet, AlertDialog) bougeaient de manière erratique lors des interactions
- Quand l'utilisateur cliquait ou mettait la souris sur la modale, elle se déplaçait vers le coin inférieur droit de l'écran
- Le problème se produisait sur desktop ET mobile
- La modale restait stable quand on n'interagissait pas avec elle

**Cause racine**:
1. **Package Vaul** installé mais non utilisé qui injectait des gestionnaires d'événements globaux sur les pointeurs
2. **Conflits CSS** entre les transformations statiques (`translate-x-[-50%] translate-y-[-50%]`) et les animations de slide qui utilisaient aussi des transformations

**Diagnostic**:
- Vaul (bibliothèque de drawers avec drag-to-dismiss) ajoutait des event handlers pour détecter le drag même sans être utilisé
- Les transformations CSS multiples (centrage + animations) créaient des conflits lors du recalcul au clic
- Le composant `Drawer` existait mais n'était importé/utilisé nulle part dans l'application

**Solution appliquée**:

**Étape 1** - Retrait de Vaul:
```bash
npm uninstall vaul
rm src/components/ui/drawer.tsx
```

**Étape 2** - Simplification du centrage CSS:

**AVANT** (problématique):
```css
fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%]
+ animations complexes avec slide-in/out
```

**APRÈS** (stable):
```css
fixed inset-0 m-auto h-fit
```

Cette approche utilise `margin: auto` pour centrer au lieu des transformations CSS, évitant ainsi les conflits.

**Fichiers modifiés**:
- `front-1/package.json` - Retrait de vaul
- `front-1/src/components/ui/drawer.tsx` - Supprimé
- `front-1/src/components/ui/dialog.tsx` - Simplification CSS
- `front-1/src/components/ui/alert-dialog.tsx` - Simplification CSS

**Commits**:
- `ea618a6` - Retrait de Vaul
- `18cf924` - Simplification du centrage des modales

**Résultat**:
✅ Modales parfaitement stables et centrées
✅ Aucun mouvement lors des interactions
✅ Fonctionne sur desktop et mobile

**Leçon apprise**:
- Toujours vérifier les packages installés mais non utilisés qui peuvent avoir des effets de bord
- Préférer les méthodes CSS simples et robustes (margin auto) aux transformations complexes
- Les conflits entre transformations CSS statiques et animations peuvent causer des comportements imprévisibles

---

## 🔧 Template pour futurs bugs

```markdown
### Bug #X: [Titre court du bug]

**Date**: [Date]

**Symptômes**:
- [Description détaillée du comportement observé]

**Cause racine**:
- [Explication technique de la cause]

**Solution appliquée**:
[Code ou commandes utilisées]

**Fichiers modifiés**:
- [Liste des fichiers]

**Commits**:
- [Hash] - [Message]

**Résultat**:
[Statut de la correction]

**Leçon apprise**:
[Ce qu'on a appris pour éviter ce type de bug à l'avenir]
```

---

## 📊 Statistiques

- **Total bugs résolus**: 1
- **Bugs critiques**: 1
- **Bugs UI/UX**: 1
- **Bugs backend**: 0

---

**Dernière mise à jour**: 25 décembre 2024
