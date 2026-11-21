# Örnek dokümanlar için beklenen bulgular

Bu liste, üç örnek dokümana bilerek yerleştirilmiş zayıflıkları ve eksikleri gösterir. Claude Code'un yazacağı `eval.py` bu listeyi "doğru cevap seti" olarak kullanabilir (`samples/expected/` altına her doküman için ayrı dosya olarak bölünebilir).

Not: Liste benim hazırladığım bir ilk taslaktır, bir güvenlik uzmanı tarafından doğrulanmamıştır. Yönetime sunmadan önce bir uzmanın gözden geçirmesi önerilir. Kimlik referansları (CWE, OWASP) örnek amaçlıdır.

## Doküman 1: Mobil bankacılık, para transferi (MB-TRF-AD-007)

| # | Bileşen / akış | STRIDE | Beklenen bulgu | Dokümandaki dayanak |
|---|---|---|---|---|
| 1-1 | Transfer Servisi | E | Hesap sahipliği kontrolü yok; kullanıcı başka müşterinin hesap numarasıyla transfer başlatabilir (BOLA/IDOR) | Bölüm 4, adım 3 |
| 1-2 | Dolandırıcılık Kontrol Servisi | D / T | Zaman aşımında işlem engellenmeden devam ediyor (fail-open); kontrol atlatılabilir | Bölüm 4, adım 5 |
| 1-3 | Transfer Servisi ↔ Limit / Dolandırıcılık servisleri | I / T | İç ağda şifrelenmemiş HTTP; araya girilip veri okunabilir ya da değiştirilebilir | Bölüm 5, 4. madde |
| 1-4 | Limit Servisi | T / E | Sayaç, işlem sonrası güncelleniyor; eşzamanlı isteklerle günlük limit aşılabilir (yarış durumu) | Bölüm 4, adım 4 ve 8; Bölüm 8 |
| 1-5 | Transfer Servisi | T | Tekrar önleme anahtarı yok; otomatik yeniden denemede aynı transfer birden fazla işlenebilir | Bölüm 4, adım 10; Bölüm 8 |
| 1-6 | Kimlik Doğrulama Servisi (OTP) | S | OTP için deneme sınırı belirtilmemiş; 6 haneli kod kaba kuvvetle denenebilir; SMS kanalı SIM değiştirme saldırısına açık | Bölüm 4, adım 6 |
| 1-7 | Merkezi Log Platformu | I | Üretimde DEBUG: istek/yanıt gövdeleri (IBAN, tutar vb.) loglanıyor; geniş erişim | Bölüm 5, 6. madde |
| 1-8 | Operasyon Paneli | S / R / E | Ortak hesap, ikinci faktör yok, limit değişikliği kaydedilmiyor (inkâr ve yetki kötüye kullanımı) | Bölüm 5, 8. madde |
| 1-9 | Mobil uygulama | T / I | Sertifika sabitleme, root/jailbreak tespiti ve kod karartma yok | Bölüm 5, 7. madde |
| 1-10 | Kimlik Doğrulama Servisi | S | Token ömrü uzun (24 saat / 30 gün) ve cihaza bağlı değil; çalınan token yeniden kullanılabilir | Bölüm 5, 2. madde |
| 1-11 | Bildirim Servisi / SMS operatörü | I | SMS bakiye bilgisi içeriyor; API anahtarı ConfigMap'te tutuluyor | Bölüm 4, adım 9; Bölüm 5, 10. ve 11. maddeler |
| 1-12 | İşlem Veritabanı / yedekler | I | Yedeklerin şifrelenip şifrelenmediği belirtilmemiş; alıcı bilgileri açık metin | Bölüm 5, 5. ve 9. maddeler |

Dokümanda belirtilmemiş (unknowns olarak çıkmalı): yedek şifrelemesi, OTP deneme sınırı, Redis erişim kontrolü.

## Doküman 2: Bireysel kredi başvuru platformu (KRD-APP-SA-003)

| # | Bileşen / akış | STRIDE | Beklenen bulgu | Dokümandaki dayanak |
|---|---|---|---|---|
| 2-1 | Başvuru Servisi (durum sorgulama) | E / I | Sıralı başvuru numarası ve sahiplik kontrolü yok; başkasının başvurusu görülebilir (BOLA, numaralandırma) | Bölüm 4, 1. madde |
| 2-2 | Belge Yükleme Servisi | T / E | Yalnızca uzantı kontrolü; içerik doğrulaması ve virüs taraması yok; zararlı dosya yüklenebilir | Bölüm 3, adım 3 |
| 2-3 | OCR servisi | I | Belgeler yurt dışındaki üçüncü taraf bölgesine gidiyor; KVKK ve veri aktarımı riski | Bölüm 4, 5. madde |
| 2-4 | Kural Yönetim Arayüzü / Karar Motoru | T / E | Kurallar ikinci kişi onayı olmadan anında canlıya yansıyor; kötü niyetli ya da hatalı değişiklik | Bölüm 4, 2. madde |
| 2-5 | Veri Ambarı | I | TCKN, gelir, borç maskesiz; 40 kişilik geniş erişim | Bölüm 4, 3. madde |
| 2-6 | Çağrı Merkezi Paneli | I | Tam TCKN ve gelir görünüyor; iç kaynaklı sızıntı | Bölüm 4, 4. madde |
| 2-7 | Model Yönetim Deposu | T | Model dosyaları paylaşımlı klasörde, sürüm ve imza kontrolü yok; model zehirleme/değiştirme | Bölüm 4, 7. madde |
| 2-8 | KYC webhook | S / T | Webhook imzası doğrulanmıyor; sahte "kimlik doğrulandı" bildirimi gönderilebilir | Bölüm 4, 9. madde |
| 2-9 | Başvuru oluşturma ucu | D | İstek sınırlaması yok; otomatik başvuru seli, kredi bürosu sorgu maliyeti ve hizmet aksaması | Bölüm 4, 11. madde |
| 2-10 | Kampanya SMS bağlantısı | S | Tek kullanımlık olmayan, 30 gün geçerli bağlantı; yeniden kullanım ve yönlendirme | Bölüm 4, 12. madde |
| 2-11 | Nesne depolama | I | İmzalı URL 7 gün geçerli; paylaşılırsa belgelere uzun süre erişim | Bölüm 4, 6. madde |
| 2-12 | Karar Motoru (ret gerekçesi) | R | Açıklanabilirlik eksikliği; ret nedeninin izlenememesi (düzenleme ve itiraz riski) | Bölüm 4, 8. madde |

Dokümanda belirtilmemiş: belge saklama süresi, selfie/biyometrik verinin silinme koşulları, log maskeleme politikası (kısmen belirtilmiş).

## Doküman 3: Açık bankacılık API platformu (OB-PLT-SA-001)

| # | Bileşen / akış | STRIDE | Beklenen bulgu | Dokümandaki dayanak |
|---|---|---|---|---|
| 3-1 | Yetkilendirme Sunucusu | S / T | redirect_uri ön ek eşleşmesiyle doğrulanıyor; yetkilendirme kodunun saldırgan adresine yönlendirilmesi (açık yönlendirme) | Bölüm 4.1, adım 1 |
| 3-2 | Yetkilendirme Sunucusu | S | Yenileme token'ı rotasyonu yok; çalınan yenileme token'ı 90 gün kullanılabilir | Bölüm 4.1, adım 4 |
| 3-3 | Rıza Yönetim Servisi | E / R | Rıza iptalinde token iptali gecikmeli; iptal sonrası erişim sürer | Bölüm 5, 3. madde |
| 3-4 | Rıza ekranı | E | Varsayılan olarak tüm hesaplar seçili; müşteri farkında olmadan fazla yetki verir | Bölüm 4.1, adım 2 |
| 3-5 | Webhook Servisi | T / I | Callback URL doğrulaması yalnızca https; iç ağ adreslerine istek (SSRF) | Bölüm 4.2, adım 4 |
| 3-6 | API Geçidi | D | Hız sınırı IP bazlı; TPP bazlı değil; tek TPP ya da paylaşılan IP arkasındaki TPP'ler etkilenebilir | Bölüm 5, 1. madde |
| 3-7 | TPP Sertifika Deposu / API Geçidi | S | Sertifika iptali günlük senkronizasyonla; iptal edilen TPP bir gün daha erişebilir | Bölüm 5, 2. madde |
| 3-8 | Geliştirici Portalı | S | MFA yok; API anahtarı e-postayla; hesap ele geçirme | Bölüm 5, 4. madde |
| 3-9 | Merkezi log | I | Erişim token'ları loglarda; geniş erişim | Bölüm 5, 6. madde |
| 3-10 | Sandbox Ortamı | I | Gerçek IBAN ve bakiyeler sandbox'ta; veri sızıntısı | Bölüm 5, 7. madde |
| 3-11 | Ödeme Başlatma Servisi | T / R | Talimat imzası (JWS) isteğe bağlı; inkâr ve bütünlük riski; SCA muafiyeti TPP beyanına göre | Bölüm 4.2, adım 2 ve 3 |
| 3-12 | Hesap Bilgisi Servisi | D / I | Sayfalama limiti istemciden alınıyor; aşırı büyük sorgularla yük ve toplu veri çekme | Bölüm 4.1, adım 5 |
| 3-13 | TPP onboarding | E | Tek yönetici onayı; sahte/hatalı TPP kaydı | Bölüm 5, 5. madde |

## Kullanım önerisi

- Her doküman için analiz sonrası bu listedeki kaç maddenin bulunduğuna bakın (recall). Hedef: ilk sürümde %60-70, kural kataloğu ve istemler iyileştikçe artırmak.
- Listede olmayan ama makul bulgular olabilir; bunlar yanlış pozitif sayılmadan önce uzman tarafından değerlendirilmelidir.
- Demo sırasında 3 dokümanı sırayla yükleyip her birinde farklı bir temayı vurgulayabilirsiniz: Doküman 1 (ödeme akışı), Doküman 2 (veri gizliliği ve üçüncü taraflar), Doküman 3 (kimlik ve yetkilendirme).
