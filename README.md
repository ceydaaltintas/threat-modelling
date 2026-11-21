# Tehdit Modelleme Platformu

Mimari dokümanlardan tehdit modeli üreten, kurum içi **yönetim demosu**.
Kullanıcı bir mimari doküman yükler; sistem dokümandan sistem modelini çıkarır,
tehditleri üretir, doğrular, puanlar, önlem önerir ve rapor hazırlar. En kritik
ekran gereksinimi, analizin **hangi adımda olduğunun canlı olarak** görülmesidir.

> **Uyarı:** Bu uygulama gerçek bankacılık ortamında kullanılmak üzere
> tasarlanmamıştır. Ürettiği tehditler dokümandan türetilen **olasılıklardır**;
> sistem testi yerine geçmez. Tüm örnek dokümanlar kurgusaldır
> ("Örnek Banka A.Ş.").

**Şu anki durum: Aşama 0 (iskelet).** Ayrıntı için aşağıdaki
"Aşama 0'da ne çalışıyor" bölümüne bakın. Görev tanımının tamamı
[docs/PROMPT.md](docs/PROMPT.md) dosyasındadır.

---

## 1. Kurulum

Gereken tek şey **Docker**'dır (Docker Desktop açık olmalı).

```bash
cp .env.example .env
docker compose up
```

İlk çalıştırma bağımlılıkları indirdiği için birkaç dakika sürer. Ardından:

| Adres | Ne |
|---|---|
| http://localhost:3000 | Arayüz |
| http://localhost:8000/api/docs | Arka uç API dokümantasyonu |
| http://localhost:8000/api/health | Sağlık kontrolü |
| localhost:5433 | PostgreSQL (kullanıcı/parola: `threatmodel`) |

Veritabanı şeması konteyner açılırken `alembic upgrade head` ile otomatik
uygulanır; elle bir adım gerekmez.

Durdurmak için:

```bash
docker compose down
```

Veritabanını da sıfırlamak için:

```bash
docker compose down -v
```

## 2. Yapılandırma

Tüm ayarlar `.env` dosyasından okunur; örnekler ve açıklamalar
`.env.example` içindedir. Önemli olanlar:

| Değişken | Varsayılan | Ne işe yarar |
|---|---|---|
| `APP_NAME` | Tehdit Modelleme Platformu | Arayüzde görünen ürün adı |
| `FRONTEND_PORT` / `BACKEND_PORT` | 3000 / 8000 | Host tarafındaki portlar |
| `LLM_PROVIDER` | `gemini_native` | LLM sağlayıcı (Aşama 1'de devreye girer) |
| `LLM_MODEL` | *(boş)* | Güncel ücretsiz/hızlı modeli siz seçersiniz |
| `LLM_API_KEY` | *(boş)* | Yalnızca ortam değişkeninden okunur, ekranda **gösterilmez** |
| `DEMO_REPLAY` | `false` | Kayıtlı çıktı modu (`true` / `strict`) — Aşama 5 |
| `OCR_ENABLED` | `false` | OCR varsayılan olarak kapalıdır |
| `RISK_THRESHOLD_*` | 4 / 9 / 16 | Risk seviyesi eşikleri |

**LLM modeli seçimi:** Ücretsiz katmanların günlük istek ve token limitleri
zamanla değişir. Kod içine sabit limit gömülmemiştir; kullanmadan önce
sağlayıcınızın güncel limit sayfasına bakıp `LLM_MODEL` değerini kendiniz
yazın. Ücretsiz katmanda gönderilen veri sağlayıcı tarafından
kullanılabileceği için bu platformda **yalnızca kurgusal örnek dokümanlar**
kullanılmalıdır.

`.env` dosyası `.gitignore` içindedir; API anahtarları depoya girmez.

## 3. Aşama 0'da ne çalışıyor

Aşama 0 iskelet aşamasıdır. **Altyapı ve akış gerçek, adım çıktıları örnek
veridir** — arayüz bunu "Örnek veri" rozetiyle ve olay günlüğünde
`[örnek veri]` etiketiyle açıkça belirtir.

Çalışanlar:

- `docker compose up` ile frontend + backend + PostgreSQL (pgvector) ayağa
  kalkar, migration'lar uygulanır, sağlık ucu yanıt verir.
- Veri modelinin **tamamı** oluşturulmuştur (proje, doküman, analiz, adım,
  sistem modeli, tehdit, bilgi tabanı, LLM çağrısı, denetim izi). Sonraki
  aşamalar yalnızca bu tabloları doldurur.
- Dokuz adımlık **dikey adım göstergesi (stepper)** gerçek bir SSE olay
  akışıyla canlı ilerler: durum ikonu, süre, sayaç, ilerleme çubuğu, anlık
  mesaj.
- **Model onayı duraklaması** gerçektir: analiz 2. adımdan sonra durur,
  "Onayla ve devam et" denene kadar bekler. "Otomatik devam" seçeneği
  duraklamayı atlar ve bunu günlüğe yazar.
- 8. adımda (uzman incelemesi) analiz yine kullanıcıyı bekler.
- Sayfa yenilendiğinde olay akışı baştan oynatılır; stepper doğru durumu
  hemen gösterir.
- Analiz başlatma ve devam etme işlemleri **denetim izine** yazılır.
- Ekran iskeletleri: Projeler, Yeni analiz (sürükle-bırak + 3 örnek senaryo
  kartı), Analiz ekranı, Özet panosu (5×5 ısı haritası dahil), Bilgi tabanı,
  Denetim izi, Ayarlar, rol değiştirici, açık/koyu tema.

Henüz **çalışmayanlar** (planlandıkları aşamalarla):

| Eksik | Aşama |
|---|---|
| Yüklenen dosyanın gerçekten okunması, metin çıkarma | 1 |
| LLM adaptörü ve `SystemModel` çıkarımı, DFD diyagramı, kanıt vurgulama | 1 |
| Bilgi tabanı (RAG), kural kataloğu, tehdit üretimi | 2 |
| Doğrulama, risk hesabı, önlem üretimi, kontrol eşleme | 3 |
| Uzman kararları, rapor (PDF/Excel/JSON), panonun gerçek verisi | 4 |
| Kayıtlı çıktı modu, `seed_demo.py`, `eval.py`, 5 dakikalık demo akışı | 5 |

"Yeniden çalıştır" ve "Bu adımı yeniden dene" düğmeleri şu an yalnızca
bilgilendirme bildirimi gösterir; gerçek işlem hattı Aşama 1'de bağlanacak.

## 4. Proje yapısı

```
backend/                 FastAPI + SQLAlchemy 2 + Alembic
  app/api/               REST ve SSE uçları
  app/pipeline/          9 adımın tanımı (steps.py) ve Aşama 0 üreticisi
  app/core/              ayarlar, veritabanı, olay veriyolu, örnek senaryolar
  app/models/            ORM varlıkları (veri modelinin tamamı)
  app/llm/ kb/ rules/    sonraki aşamalarda doldurulacak modüller
  app/risk/ controls/    "
  app/reports/ audit/    "
  alembic/versions/      migration'lar
  tests/                 birim testleri
frontend/
  src/app/               sayfalar (App Router)
  src/components/        arayüz bileşenleri (analysis/, layout/, ui/)
  src/lib/               API istemcisi, tipler, Türkçe biçimlendirme
samples/
  documents/             3 kurgusal mimari doküman (PDF)
  expected/              beklenen bulgular (değerlendirme için)
docs/PROMPT.md           ana görev tanımı
```

## 5. Geliştirme

Backend ve frontend `docker compose` içinde sıcak yeniden yükleme ile
çalışır; dosyayı kaydetmeniz yeterlidir.

```bash
# Backend testleri
docker compose exec backend python -m pytest -q

# Frontend tip kontrolü
docker compose exec frontend npx tsc --noEmit

# Yeni migration üretmek
docker compose exec backend alembic revision --autogenerate -m "açıklama"
docker compose exec backend alembic upgrade head

# Logları izlemek
docker compose logs -f backend
```

## 6. Roller ve kimlik doğrulama

Sağ üstteki rol değiştirici (**Güvenlik Uzmanı** / **Yönetici (salt okunur)**)
yalnızca demo içindir, gerçek bir kimlik doğrulama değildir. Gerçek bir
kurulumda kurumun kendi kimlik sistemi (SSO) bu noktaya bağlanır; şu an rol
bilgisi `x-demo-role` başlığıyla taşınır ve denetim izine yazılır.

## 7. Sorun giderme

**`docker compose up` "port is already allocated" diyor.**
Başka bir uygulama 3000, 8000 veya 5433 portunu kullanıyor. `.env` içindeki
`FRONTEND_PORT`, `BACKEND_PORT` veya `POSTGRES_PORT` değerlerini değiştirin.
`BACKEND_PORT` değiştirirseniz `NEXT_PUBLIC_API_BASE_URL` adresini de aynı
porta çekin, sonra `docker compose up -d` ile yeniden başlatın.

**Arayüz "Arka uca ulaşılamadı" diyor.**
`docker compose ps` ile `backend` servisinin ayakta olduğunu doğrulayın,
`curl http://localhost:8000/api/health` deneyin ve `.env` içindeki
`NEXT_PUBLIC_API_BASE_URL` değerinin `BACKEND_PORT` ile aynı portu
gösterdiğinden emin olun.

**Adım göstergesi ilerlemiyor / olay günlüğü boş.**
Olay akışı SSE ile gelir. Olay günlüğündeki rozet "Bağlı (SSE)" demiyorsa
tarayıcı konsolunu ve `docker compose logs backend` çıktısını kontrol edin.

**Veritabanı hatası veya tablo bulunamadı.**
`docker compose exec backend alembic upgrade head` çalıştırın. Sorun sürerse
`docker compose down -v && docker compose up` ile sıfırdan kurun (tüm veriler
silinir).

**Docker daemon'a bağlanılamıyor.**
Docker Desktop'ın açık ve çalışır durumda olduğundan emin olun.

## 8. Lisans ve atıflar

Kullanılan üçüncü taraf paketler ve veri kaynakları lisanslarıyla birlikte
[THIRD_PARTY.md](THIRD_PARTY.md) dosyasında listelenir. Telifli standartların
(ISO 27001, PCI DSS) tam metni bilgi tabanına konmaz; yalnızca madde kimliği
ve bu projede yazılmış kısa özet saklanır.
