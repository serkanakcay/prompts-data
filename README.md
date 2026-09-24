# AI Prompts & Images Data API

Bu depo, [PromptPlum](https://promptplum.com/libraries/) üzerindeki prompt ve görsel verilerini kategorize ederek mobil uygulamalar için CDN/REST API formatında sunar.

---

## 📱 Mobil Uygulama API Kullanımı

Mobil uygulamanızdan (SwiftUI, UIKit, Flutter, React Native vb.) aşağıdaki CDN URL'lerini doğrudan `GET` isteğiyle çağırabilirsiniz. 

> **Not:** jsDelivr CDN kullanıldığı için GitHub rate-limit sınırına takılmaz, hızlı ve global olarak önbelleklenir.

### 0. Mobil Anasayfa API (Manşet & İlk 3 Kategori)
Uygulama açılışında manşeti ve altındaki ilk 3 kategoriyi tek istekte getiren ana endpoint:
```http
GET https://cdn.jsdelivr.net/gh/serkanakcay/prompts-data@main/data/home.json
```
- **Manşet Alanı:** `headline` objesi (sizin belirlediğiniz kategori, örn: Hollywood)
- **İlk 3 Kategori:** `initial_categories` ve `sections` (Portraits, Cinematic, Cyberpunk vb.)

### 1. Kategori Listesi (Ana Menü / Keşfet)
Tüm kategorilerin listesi, prompt sayıları ve ilgili kategori JSON bağlantıları:
```http
GET https://cdn.jsdelivr.net/gh/serkanakcay/prompts-data@main/data/categories.json
```

### 2. Kategori Detayı (Örn: Hollywood)
Kategoriye ait tüm promptlar, açıklamalar, araçlar, beğeni sayıları ve görseller:
```http
GET https://cdn.jsdelivr.net/gh/serkanakcay/prompts-data@main/data/hollywood.json
```

### 3. Görseller
Her bir prompt objesinde görsellerin doğrudan CDN URL'leri yer alır:
```http
GET https://cdn.jsdelivr.net/gh/serkanakcay/prompts-data@main/images/hollywood/Gemini_Generated_Image_7eu1u37eu1u37eu1.jpg
```

---

## 🛠 Veri Formatı (JSON Yapısı)

```json
{
  "category": "Hollywood",
  "slug": "hollywood",
  "total_prompts": 8,
  "updated_at": "2026-09-24T12:35:19Z",
  "prompts": [
    {
      "id": "6a15472c564f4ca152670208",
      "title": "Venom action",
      "slug": "venom-action",
      "category": "Hollywood",
      "category_slug": "hollywood",
      "prompt": "Create a 16K ultra-realistic, cinematic Hollywood action scene using the uploaded reference image...",
      "description": "...",
      "ai_tools": ["Gemini"],
      "like_count": 52,
      "view_count": 2281,
      "copy_count": 2348,
      "is_premium": false,
      "images": [
        {
          "filename": "Gemini_Generated_Image_7eu1u37eu1u37eu1.jpg",
          "cdn_url": "https://cdn.jsdelivr.net/gh/serkanakcay/prompts-data@main/images/hollywood/Gemini_Generated_Image_7eu1u37eu1u37eu1.jpg",
          "raw_github_url": "https://raw.githubusercontent.com/serkanakcay/prompts-data/main/images/hollywood/Gemini_Generated_Image_7eu1u37eu1u37eu1.jpg",
          "width": 1187,
          "height": 1769,
          "alt": "Venom action image"
        }
      ]
    }
  ]
}
```

---

## ⚡ Scraper Kullanımı

Tüm kategorileri veya tek bir kategoriyi güncellemek için:

```bash
# Sadece Hollywood kategorisini çekmek için:
python3 scraper.py --category hollywood

# Tüm kategorileri (311 kategori) sırayla çekmek için:
python3 scraper.py --all

# Mevcut kategorileri listelemek için:
python3 scraper.py --list-categories
```
