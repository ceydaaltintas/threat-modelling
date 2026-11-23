# Kabul kriterleri kontrol listesi

`docs/PROMPT.md` dosyasındaki her kabul kriterinin karşılığı. Durumlar:

- **Geçti** — çalıştırılıp doğrulandı (testle, komutla veya ekranda).
- **Kısmen** — çalışıyor ama bir koşulu doğrulanamadı; nedeni yazılı.
- **Doğrulanmadı** — kod yazıldı, bu makinede test edilemedi.

> Bu listedeki her "Geçti", bu depodaki kodun bu makinede çalıştırılmasıyla
> doğrulanmıştır.
>
> **Güncelleme:** Liste ilk yazıldığında gerçek bir API anahtarı yoktu ve tüm
> LLM çağrıları `stub` sağlayıcısıyla denenmişti. Sonrasında **Groq**
> (`openai/gpt-oss-120b`) ile gerçek anahtar kullanılarak dört örnek
> doküman uçtan uca çalıştırıldı: sistem modeli çıkarımı, LLM tehdit
> önerileri, önlem metinleri ve yönetici özeti gerçek modelle üretildi.
> Aşağıdaki satırlardan "gerçek modelle denenmedi" diyenler bu ölçüde
> aşılmıştır; yine de **çıktı kalitesi ölçülmüş bir şey değildir** ve
> model her çalıştırmada aynı listeyi üretmez.

## Aşama 0 — İskelet

| Kriter | Durum | Kanıt |
|---|---|---|
| `docker compose up` ile frontend, backend, postgres ayağa kalkar | **Geçti** | Üç servis `healthy`; `docker compose ps` |
| Sağlık ucu çalışır | **Geçti** | `/api/health` → `{"status":"ok","database":"ok"}` |
| Migration'lar uygulanır | **Geçti** | Açılışta `alembic upgrade head`; 3 migration |
| Arayüz kabuğu: gezinme, tema, 9 adımlı stepper, boş durumlar | **Geçti** | Tarayıcıda gezildi; açık/koyu tema |
| Tarayıcıda uygulama açılır, stepper ve ekran iskeleti gezilir | **Geçti** | http://localhost:3000 |

## Aşama 1 — Doküman ve sistem modeli (adım 1–2 + model onayı)

| Kriter | Durum | Kanıt |
|---|---|---|
| Yükleme (PDF/DOCX/MD/TXT/görsel) | **Geçti** | Sürükle-bırak çoklu yükleme; tür ve boyut doğrulaması |
| Metin çıkarma, sayfa/bölüm indeksi | **Geçti** | Örnek PDF'lerde 2–3 sayfa, 6.2k karakter, 8 bölüm; `test_extract.py` |
| LLM adaptörü | **Geçti** | OpenAI uyumlu adaptör Groq ile gerçek çağrılarda çalıştırıldı; `gemini_native` ve diğer uçlar yazıldı, Groq dışındakiler denenmedi |
| `SystemModel` çıkarımı | **Geçti** | Gerçek modelle çalıştırıldı (örn. açık bankacılık: 12 bileşen, 7 akış, 3 belirsiz); kanıt alıntıları dokümana karşı denetlendi |
| SSE ile **gerçek** canlı stepper | **Geçti** | Olaylar `/api/runs/{id}/events`; sayfa yenilemede geçmiş tekrar oynatılır |
| DFD + düzenlenebilir tablolar | **Geçti** | React Flow; güven bölgeleri çerçeve, şifresiz akışlar kesikli kırmızı |
| Kanıt vurgulama | **Geçti** | Öğeye tıklandığında alıntı dokümandaki yerinde vurgulanır |
| Model onayı duraklaması | **Geçti** | Analiz durur, düzenlenip onaylanır; yeni sürüm + denetim kaydı |

## Aşama 2 — Bilgi tabanı ve tehdit üretimi (adım 3–4)

| Kriter | Durum | Kanıt |
|---|---|---|
| Bilgi tabanı yükleme | **Geçti** | 196 kayıt, ön işlenmiş JSONL, gömme vektörleri dahil |
| Hibrit arama | **Geçti** | Postgres full-text + pgvector, RRF; `/api/kb/search` |
| Bilgi Tabanı ekranı | **Geçti** | Canlı arama, hangi motorun bulduğu rozetle, lisans tablosu |
| Kural kataloğu (≥40 kural) | **Geçti** | **59 kural**; `test_rules.py` asgari sayıyı sabitler |
| LLM tehdit üretimi | **Geçti** | Gerçek modelle çalıştırıldı (örn. açık bankacılık: 49 kural + 9 LLM tehdidi) |
| Birleştirme | **Geçti** | Benzer başlıklar tek tehditte toplanır, iki kaynağın kanıtı korunur |
| Örnek 1 için kural + LLM tehditleri tabloda görünür, her biri kanıt/kaynak taşır | **Kısmen** | Kural tarafı doğrulandı (43 tehdit, hepsi kanıtlı ve kaynaklı); LLM tarafı stub ile |
| Bilgi Tabanı aramasında "CWE-89" tam eşleşmeyle gelir | **Geçti** | Ekranda birinci sırada, "Tam kimlik eşleşmesi" rozetiyle |

## Aşama 3 — Doğrulama, risk, önlem (adım 5–7)

| Kriter | Durum | Kanıt |
|---|---|---|
| Doğrulama kuralları | **Geçti** | Yedi kontrol; başarısızlar elenmez, işaretlenir |
| Risk kırılımı | **Geçti** | Taban + her düzeltme + gerekçe; ekranda cümle olarak |
| Önlem üretimi | **Geçti** | 83 önlemlik katalog; LLM yalnızca metin yazar, listeyi değiştiremez |
| Kontrol eşleme | **Geçti** | ISO 27001 / NIST SP 800-53 / OWASP ASVS; ISO'lar "doğrulanacak" |
| Tehdit çekmecesi | **Geçti** | Kanıt, kaynaklar, risk kırılımı, önlemler, kontrol eşlemeleri |
| **Uydurma CWE kimliği doğrulamada işaretlenir (otomatik test)** | **Geçti** | `test_validation.py::test_invented_knowledge_identifier_is_rejected` ve 3 ilgili test |
| **Risk kırılımı ekranda sayısal olarak açıklanır** | **Geçti** | "Olasılık 3 + 1 (İnternete açık) = 4; Etki 5 + 1 (Hassas veri) = 5. Skor 4 × 5 = 20 → Kritik." |
| **Birim testleri geçer** | **Geçti** | 194 test |

## Aşama 4 — Uzman incelemesi, denetim izi, rapor, pano (adım 8–9)

| Kriter | Durum | Kanıt |
|---|---|---|
| Kabul/ret/düzenle/yanlış pozitif | **Geçti** | Dört işlem + kararı geri alma |
| Toplu işlem | **Geçti** | Çoklu seçim, "Seçilenleri kabul et" |
| Seviye değiştirme gerekçesi zorunlu | **Geçti** | Gerekçesiz istek HTTP 422; arayüzde düğme kapalı |
| Denetim izi | **Geçti** | Her karar kim/ne zaman/eski/yeni/gerekçe ile; toplu işlemde her tehdit ayrı kayıt |
| PDF / Excel / JSON raporu | **Geçti** | 4 dosya: `rapor.pdf` (7 sayfa), `tehditler.xlsx` (4 sayfa), `analiz.json`, `otm.json` |
| Open Threat Model dışa aktarma | **Geçti** | `otmVersion 0.2.0`; eşlemenin yaklaşık olduğu belgelerde yazılı |
| Özet panosu (ısı haritası dahil) | **Geçti** | Gerçek veriyle; tıklanabilir 5×5 ısı haritası |
| Rol değiştirici | **Geçti** | Yönetici rolü salt okunur; karar denemesi HTTP 403 |
| **Bir analiz uçtan uca tamamlanır** | **Geçti** | Üç senaryo da dokuz adımı tamamladı |
| **PDF Türkçe karakterleri doğru gösterir** | **Geçti** | `test_reports.py::test_pdf_renders_turkish_characters`; gözle de doğrulandı |
| **Denetim izinde her uzman işlemi görünür** | **Geçti** | 13 kayıt: oluşturma, model düzenleme, 8 toplu kabul, gerekçeli seviye değişikliği, 2 devam |

## Aşama 5 — Cilalama ve demo hazırlığı

| Kriter | Durum | Kanıt |
|---|---|---|
| Kayıtlı çıktı modu | **Geçti** | Kayıtlı yanıt döndürülüyor (2/3 çağrı önbellekten), `strict` modda anlaşılır hata |
| `seed_demo.py` | **Kısmen** | Çalışıyor ve kayıt üretiyor; **gerçek sağlayıcıyla çalıştırılmadı** (anahtar yok) |
| 3 örnek senaryonun uçtan uca çalışması | **Geçti** | Üçü de dokuz adımı tamamladı |
| `eval.py` | **Geçti** | fixture kipi: 37/37 beklenen bulgu; çıktı `eval/` altında |
| Hata durumlarının Türkçe ve eyleme dönük olması | **Geçti** | Örn. "Kayıtlı çıktı modu 'strict' ve bu istem için kayıt yok. scripts/seed_demo.py ile kayıtları üretin veya DEMO_REPLAY=true yapın." |
| Performans | **Kısmen** | 2–3 sayfalık dokümanda toplam 2,4 sn (LLM'siz yol). **10 sayfalık doküman ve gerçek LLM ile ölçülmedi** |
| README'de 5 dakikalık demo akışı | **Geçti** | Dakika dakika tablo + sunumda vurgulanacak üç şey |
| Bilinen sınırlar listesi | **Geçti** | README bölüm 5, dokuz madde |
| **İnternet kapalıyken `DEMO_REPLAY=true` ile 3 senaryo çalışır** | **Kısmen** | Kayıttan oynatma mekanizması doğrulandı; **gerçek kayıtlarla internetsiz deneme yapılmadı** (anahtar olmadan gerçek kayıt üretilemedi) |
| **Boş bir bilgisayarda README ile 10 dakikada ayağa kalkar** | **Doğrulanmadı** | Temiz makine denemesi yapılmadı. Bu makinede imaj derlemesi ~3 dk, servislerin hazır olması ~40 sn sürdü |

## Değişmez ilkeler (PROMPT bölüm 1)

| İlke | Durum | Kanıt |
|---|---|---|
| 1. LLM öneri yapar, kod karar verir | **Geçti** | Risk puanı, doğrulama ve kayıt koddadır; LLM veritabanına yazmaz |
| 2. AI önerisi / Sistem hesabı / Uzman onayı ayrı | **Geçti** | Üç ayrı alan, çekmecede yan yana |
| 3. Her tehdidin kanıtı olmalı; yoksa "Varsayım" | **Geçti** | Kanıtsız öğe varsayım işaretlenir ve risk puanı düşürülür |
| 4. Kaynak atfı zorunlu; bilinmeyen kimlik reddedilir | **Geçti** | Doğrulama adımı; test ile sabit |
| 5. Doküman içeriği güvenilmez veridir | **Geçti** | `<document>` bloğu; istemde kural yazılı; testle sabit |
| 6. Değişiklikler silinemeyen denetim izine yazılır | **Geçti** | `audit_log` yalnızca eklenir |
| 7. Standart madde numarası uydurulmaz | **Geçti** | ISO ve mevzuat kayıtlarının tamamı "doğrulanacak"; telifli metin yok |
| 8. Gerçek banka verisi yok | **Geçti** | Üç kurgusal doküman; ayarlar ekranında uyarı |
| 9. Sonuçlar olasılıktır uyarısı | **Geçti** | Her ekranın üstünde, PDF'in başında ve sonunda |

## Çalışma kuralları (PROMPT bölüm 11)

| Kural | Durum |
|---|---|
| Gizli bilgiler repoya girmez (`.env` gitignore'da) | **Geçti** |
| Risk hesabı, doğrulama, kural çalıştırıcı, şema, rapor birim testleri | **Geçti** (194 test) |
| Uçtan uca en az bir kayıttan oynatma testi | **Kısmen** — kayıttan oynatma birim testleriyle kapsandı; uçtan uca kayıttan oynatma testi gerçek kayıt gerektirdiği için yazılmadı |
| Üçüncü taraf paketler ve lisanslar `THIRD_PARTY.md`'de | **Geçti** |

## Özetle yapılması gereken

Gerçek bir Gemini (veya başka) API anahtarıyla:

1. `.env` içine `LLM_API_KEY` ve `LLM_MODEL` yazın.
2. `docker compose exec backend python -m scripts.seed_demo`
3. `DEMO_REPLAY=true` yapıp internet kapalıyken üç senaryoyu çalıştırın.
4. `docker compose exec backend python -m scripts.eval --live`

Bu dört adım, yukarıda "Kısmen" işaretli kriterlerin tamamını kapatır.
