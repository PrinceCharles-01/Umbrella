# 📝 Configuration Google Vision Credentials

## ⚡ ACTION REQUISE

Placez votre fichier de credentials Google Vision **exactement ici** :

```
django-backend/google-vision-credentials.json
```

**Chemin complet** :
```
C:\Users\Charles\Desktop\Umbrella-1\django-backend\google-vision-credentials.json
```

---

## ✅ Vérification

Le fichier doit s'appeler **exactement** :
```
google-vision-credentials.json
```

PAS :
- ❌ `google-vision-credentials.json.txt`
- ❌ `credentials.json`
- ❌ `google-vision-credentials (1).json`

---

## 🔄 Après avoir placé le fichier

1. **Redémarrer le backend** :
   ```bash
   cd django-backend
   python manage.py runserver 0.0.0.0:3001
   ```

2. **Vérifier le mode** :

   Au démarrage du serveur, vous devriez voir dans les logs :
   ```
   Mode OCR: Production (Google Vision)
   ```

   Si vous voyez :
   ```
   WARNING: Fichier google-vision-credentials.json non trouvé. Mode MOCK activé.
   ```
   → Le fichier n'est pas au bon endroit ou mal nommé

3. **Tester** :
   ```bash
   python manage.py shell
   ```

   ```python
   from api.services import OCRService
   service = OCRService()
   if service.client:
       print("✅ Google Vision OK")
   else:
       print("❌ Problème")
   ```

---

## 📁 Structure attendue

```
django-backend/
├── api/
├── umbrella_api/
├── manage.py
├── google-vision-credentials.json  ← ICI !
├── test_images/
└── ocr_logs/
```

---

## 🔒 Sécurité

⚠️ **IMPORTANT** :
- Ce fichier contient des clés privées
- NE PAS le committer sur Git (déjà dans .gitignore)
- NE PAS le partager publiquement
- Ne l'utiliser que pour ce projet

---

## ❓ Où obtenir ce fichier ?

Si vous n'avez pas encore le fichier, suivez :
1. `GOOGLE_VISION_SETUP.md` (guide complet)
2. `CONFIGURATION_GOOGLE_VISION_RAPIDE.md` (guide 5 min)

Ou demandez-moi, je peux vous guider !

---

**Une fois placé → Système prêt à scanner de vraies ordonnances ! 🚀**
