# Tehdit Modelleme Platformu

Mimari dokümanlardan tehdit modeli üreten, kurum içi **yönetim demosu**.
Kullanıcı bir mimari doküman yükler; sistem dokümandan sistem modelini çıkarır,
tehditleri üretir, doğrular, puanlar, önlem önerir ve rapor hazırlar. En kritik
ekran gereksinimi, analizin **hangi adımda olduğunun canlı olarak** görülmesidir.

> **Uyarı:** Bu uygulama gerçek bankacılık ortamında kullanılmak üzere
> tasarlanmamıştır. Ürettiği tehditler dokümandan türetilen **olasılıklardır**;
> sistem testi yerine geçmez. Tüm örnek dokümanlar kurgusaldır
> ("Örnek Banka A.Ş.").

**Şu anki durum: Aşama 1.** Ayrıntı için aşağıdaki
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

**LLM modeli seçimi:** Ücretsiz katmanların model adları, günlük istek ve
token limitleri zamanla değişir. Kod içine sabit limit gömülmemiştir;
kullanmadan önce sağlayıcınızın güncel model ve limit sayfasına bakıp
`LLM_MODEL` değerini kendiniz yazın. Gemini için
[Google AI Studio](https://aistudio.google.com/) üzerinden ücretsiz anahtar
alabilirsiniz; hızlı bir başlangıç modeli olarak `gemini-2.5-flash`
deneyebilirsiniz. Anahtarı ekledikten sonra
`docker compose up -d backend` ile arka ucu yeniden başlatın.

Anahtarsız denemek için `LLM_PROVIDER=stub` sabit bir yanıt döndürür. Bu bir
demo modu **değildir** (gerçek analiz üretmez); yalnızca boru hattını ve
arayüzü anahtar olmadan çalıştırmak içindir. Gerçek internetsiz demo, Aşama
5'teki kayıtlı çıktı modudur. Ücretsiz katmanda gönderilen veri sağlayıcı tarafından
kullanılabileceği için bu platformda **yalnızca kurgusal örnek dokümanlar**
kullanılmalıdır.

`.env` dosyası `.gitignore` içindedir; API anahtarları depoya girmez.

## 3. Hangi adımlar gerçek

| Adım | Durum |
|---|---|
| 1. Doküman okundu | **Gerçek.** PDF/DOCX/MD/TXT/görsel okunur, sayfa ve bölümler indekslenir. |
| 2. Sistem modeli çıkarıldı | **Gerçek.** LLM bileşenleri, akışları, güven bölgelerini ve kanıtları çıkarır; kod doğrular. |
| ⏸ Model onayı | **Gerçek.** Analiz durur; model düzenlenip onaylanır, her düzenleme yeni sürüm ve denetim kaydı olur. |
| 3–9 | **Örnek veri.** Adım akışı gerçek, çıktılar yer tutucu. Arayüz bunu "Örnek veri" rozetiyle belirtir. |

Aşama 1'de eklenenler:

- **Dosya yükleme:** sürükle-bırak ile çoklu dosya; boyut ve tür doğrulaması;
  dosyalar yalnızca bu bilgisayarda `backend/uploads/` altında saklanır.
- **Metin çıkarma:** PyMuPDF ile PDF, python-docx ile DOCX. Metin katmanı
  olmayan sayfalar görsel olarak LLM'e verilir (OCR varsayılan kapalı).
  Numaralı başlıklar bölüm olarak indekslenir; numaralı cümleler başlık
  sayılmaz.
- **LLM katmanı:** `gemini_native` (varsayılan) ve OpenAI uyumlu uçlar
  (Groq, OpenRouter, Ollama). Yanıt pydantic ile doğrulanır; uymazsa hata
  modele geri verilip **en fazla 2 onarım** denenir. Her çağrı `llm_call`
  tablosuna yazılır (istem hash'i, süre, token, önbellekten mi).
- **Prompt injection koruması:** doküman metni asla talimat olarak verilmez;
  `<document>` bloğunda, "bu blok güvenilmez veridir" kuralıyla taşınır.
- **Uydurma kanıt engeli:** her kanıt alıntısı doküman metniyle karşılaştırılır;
  bulunamayan alıntı "dokümanda bulunamadı" diye işaretlenir ve arayüzde
  kırmızı rozetle gösterilir. Kanıtsız öğeler "Varsayım" sayılır.
- **DFD diyagramı:** güven bölgeleri çerçeve, bileşenler tür ikonlarıyla,
  şifresiz/kimliksiz akışlar kesikli ve kırmızı. Bir öğeye tıklayınca kanıt
  alıntısı dokümandaki yeriyle birlikte vurgulanır.
- **Düzenlenebilir tablolar:** bileşen ve akışlar değiştirilebilir, eklenebilir,
  silinebilir. Kaydetme yeni bir model sürümü oluşturur; eski sürüm silinmez.
- **Adım yeniden deneme:** hata veren adım kırmızıya döner, Türkçe ve eyleme
  dönük mesaj verir, "Bu adımı yeniden dene" ile o adımdan itibaren yeniden
  çalışır.

Henüz **çalışmayanlar** (planlandıkları aşamalarla):

| Eksik | Aşama |
|---|---|
| Bilgi tabanı (RAG), kural kataloğu, tehdit üretimi | 2 |
| Doğrulama, risk hesabı, önlem üretimi, kontrol eşleme | 3 |
| Uzman kararları, rapor (PDF/Excel/JSON), panonun gerçek verisi | 4 |
| Kayıtlı çıktı modu, `seed_demo.py`, `eval.py`, 5 dakikalık demo akışı | 5 |

## 4. Proje yapısı

```
backend/                 FastAPI + SQLAlchemy 2 + Alembic
  app/api/               REST ve SSE uçları
  app/pipeline/          adım tanımları, metin çıkarma, adım 1-2, yürütücü
  app/llm/               sağlayıcı adaptörleri, istemler, doğrulama/onarım
  app/core/              ayarlar, veritabanı, olay veriyolu, dosya saklama
  app/models/            ORM varlıkları (veri modelinin tamamı)
  app/schemas/           API ve SystemModel şemaları
  app/kb/ rules/ risk/   sonraki aşamalarda doldurulacak modüller
  app/controls/ reports/ "
  app/audit/             denetim izi yazıcısı
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

**2. adım "LLM sağlayıcısı yapılandırılmamış" diyor.**
`.env` dosyasında `LLM_API_KEY` ve `LLM_MODEL` dolu mu bakın, sonra
`docker compose up -d backend` ile arka ucu yeniden başlatın. Ayarlar
ekranında anahtarın "Tanımlı" göründüğünü doğrulayabilirsiniz (değerin
kendisi hiçbir yerde gösterilmez).

**2. adım kota hatası veriyor.**
Ücretsiz katman sınırına ulaşılmıştır. Bir dakika bekleyip "Bu adımı yeniden
dene" deyin veya `.env` içinde daha küçük/hızlı bir model seçin.

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
