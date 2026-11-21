"""Hand-built system model for sample document 2 (KRD-APP-SA-003).

Used by the evaluation harness so rule coverage can be measured without an
LLM. The content mirrors the document; evidence quotes are taken verbatim
from the extracted text.
"""

from __future__ import annotations


def _c(cid, name, ctype, tech, zone, internet, quote, auth=None):
    return {
        "id": cid,
        "name": name,
        "type": ctype,
        "technology": tech,
        "trust_zone": zone,
        "internet_facing": internet,
        "authentication": auth,
        "evidence": [{"quote": quote, "page": 1}],
    }


CREDIT_APPLICATION_MODEL = {
    "components": [
        _c("musteri-portali", "Müşteri Portalı ve Mobil Uygulama", "web_app",
           "React, iOS/Android", "İnternet", True,
           "Başvurunun alındığı web portalı ve mobil uygulama."),
        _c("api-gecidi", "WAF ve API Geçidi", "gateway",
           "Kurumsal WAF, API Geçidi", "DMZ", True,
           "Dış isteklerin karşılandığı katman."),
        _c("basvuru-servisi", "Başvuru Servisi", "api",
           "Node.js (NestJS), PostgreSQL", "Uygulama", False,
           "Başvuru yaşam döngüsünü yönetir; durum sorgulama ve webhook "
           "uçlarını sunar."),
        _c("kyc-servisi", "Uzaktan Kimlik Doğrulama (KYC) Servisi", "external",
           "Üçüncü taraf KYC sağlayıcısı, webhook", "Üçüncü Taraf", True,
           "NFC ile kimlik kartı çipi okuma ve canlılık testli selfie "
           "karşılaştırması"),
        _c("belge-yukleme", "Belge Yükleme Servisi", "service",
           "Nesne depolama (S3 uyumlu), dosya yükleme", "Uygulama / Veri", False,
           "Maaş bordrosu, SGK dökümü ve gelir belgelerini"),
        _c("ocr-servisi", "OCR ve Belge Analiz Servisi", "external",
           "Bulut OCR API'si (yurt dışı bölge), saas", "Üçüncü Taraf", True,
           "Belgelerden gelir bilgisini çıkarır."),
        _c("karar-motoru", "Karar Motoru", "service",
           "Python, kural motoru, ML modeli", "Uygulama", False,
           "Kural motoru ve makine öğrenmesi tabanlı kredi skor modeli"),
        _c("kural-arayuzu", "Kural Yönetim Arayüzü", "admin",
           "Web uygulaması, kural, parametre", "Uygulama (yönetim)", False,
           "Kredi politikası ekibi eşik değerlerini ve kuralları değiştirir."),
        _c("kredi-burosu", "Kredi Bürosu Entegrasyonu", "external",
           "REST, karşılıklı TLS (mTLS), sertifika", "Üçüncü Taraf", True,
           "Skor ve borç bilgisi sorgusu."),
        _c("crm", "Müşteri Bilgi Sistemi (CRM)", "database",
           "Kurumsal CRM", "Veri", False,
           "Müşteri profili ve iletişim bilgileri."),
        _c("cekirdek", "Çekirdek Bankacılık", "external",
           "Mainframe", "Çekirdek", False,
           "Kredi tahsisi ve müşteri hesabına aktarım."),
        _c("eimza", "Sözleşme ve e-İmza Servisi", "service",
           "Java, e-imza sağlayıcı", "Uygulama / Üçüncü Taraf", False,
           "Sözleşme PDF'i üretir, mobil imza ile imzalatır."),
        _c("bildirim", "Bildirim Servisi", "service",
           "Spring Boot, sms, bağlantı, kampanya", "Uygulama", False,
           "SMS, e-posta ve push bildirimleri."),
        _c("veri-ambari", "Veri Ambarı", "database",
           "Kurumsal veri ambarı, raporlama, analitik", "Veri", False,
           "Analitik ekipler için başvuru verilerinin kopyalandığı kurumsal "
           "veri ambarı"),
        _c("cagri-merkezi", "Çağrı Merkezi Paneli", "admin",
           "Web uygulaması", "Uygulama (yönetim)", False,
           "Temsilcilerin başvuru durumunu ve müşteri bilgilerini "
           "görüntülediği panel."),
        _c("model-deposu", "Model Yönetim Deposu", "llm",
           "Ağ paylaşım klasörü, model, ml", "Yönetim", False,
           "Veri bilimi ekibinin skor modeli dosyalarını tuttuğu paylaşımlı "
           "depo"),
        _c("log-platformu", "Merkezi Log ve Metrik Platformu", "other",
           "log, izleme, metrik", "Uygulama", False,
           "İzleme için merkezi log ve metrik platformu kullanılır"),
        _c("otp-oturum", "Başvuru Oturumu ve OTP", "auth",
           "SMS OTP, doğrulama kodu", "Uygulama", False,
           "telefon numarasına gönderilen SMS OTP ile başvuru oturumu açılır",
           auth="SMS OTP"),
    ],
    "data_flows": [
        {
            "id": "f-portal-gecit", "source_id": "musteri-portali",
            "target_id": "api-gecidi", "protocol": "HTTPS",
            "encrypted": True, "authenticated": True,
            "data_classes": ["TCKN", "gelir", "pii"],
            "evidence": [{"quote": "Dış isteklerin karşılandığı katman.", "page": 1}],
        },
        {
            "id": "f-gecit-basvuru", "source_id": "api-gecidi",
            "target_id": "basvuru-servisi", "protocol": "HTTP",
            "encrypted": "unknown", "authenticated": True,
            "data_classes": ["TCKN", "başvuru"],
            "evidence": [],
        },
        {
            "id": "f-belge-ocr", "source_id": "belge-yukleme",
            "target_id": "ocr-servisi", "protocol": "HTTPS (imzalı URL)",
            "encrypted": True, "authenticated": True,
            "data_classes": ["belge", "gelir", "pii"],
            "evidence": [{
                "quote": "yüklenen belge imzalı bir URL ile OCR sağlayıcısına "
                         "gönderilir", "page": 2}],
        },
        {
            "id": "f-basvuru-buro", "source_id": "basvuru-servisi",
            "target_id": "kredi-burosu", "protocol": "REST, mTLS",
            "encrypted": True, "authenticated": True,
            "data_classes": ["TCKN", "borç"],
            "evidence": [{"quote": "Kredi bürosu bağlantısı mTLS ile korunur",
                          "page": 2}],
        },
        {
            "id": "f-kyc-webhook", "source_id": "kyc-servisi",
            "target_id": "basvuru-servisi", "protocol": "HTTPS webhook",
            "encrypted": True, "authenticated": False,
            "data_classes": ["kimlik bilgisi", "biyometrik"],
            "evidence": [{
                "quote": "KYC sağlayıcısından gelen webhook çağrıları kaynak IP "
                         "beyaz listesiyle sınırlandırılmıştır; mesaj imzası "
                         "doğrulanmaz.", "page": 2}],
        },
        {
            "id": "f-basvuru-ambar", "source_id": "basvuru-servisi",
            "target_id": "veri-ambari", "protocol": "ETL",
            "encrypted": "unknown", "authenticated": "unknown",
            "data_classes": ["TCKN", "gelir", "borç", "pii"],
            "evidence": [{"quote": "Başvuru verileri her gece Veri Ambarı'na "
                                   "kopyalanır.", "page": 2}],
        },
        {
            "id": "f-basvuru-cekirdek", "source_id": "basvuru-servisi",
            "target_id": "cekirdek", "protocol": "mesaj",
            "encrypted": "unknown", "authenticated": "unknown",
            "data_classes": ["hesap bilgisi", "tutar"],
            "evidence": [{"quote": "Çekirdek bankacılığa tahsis mesajı "
                                   "gönderilir", "page": 2}],
        },
        {
            "id": "f-basvuru-log", "source_id": "basvuru-servisi",
            "target_id": "log-platformu", "protocol": "log",
            "encrypted": "unknown", "authenticated": "unknown",
            "data_classes": ["TCKN", "gelir", "pii"],
            "evidence": [{"quote": "başvuru verisi içeren alanlar loglarda "
                                   "maskelenmez", "page": 2}],
        },
    ],
    "trust_zones": [
        {"id": "internet", "name": "İnternet"},
        {"id": "dmz", "name": "DMZ"},
        {"id": "uygulama", "name": "Uygulama"},
        {"id": "veri", "name": "Veri"},
        {"id": "cekirdek", "name": "Çekirdek"},
        {"id": "ucuncu-taraf", "name": "Üçüncü Taraf"},
        {"id": "yonetim", "name": "Yönetim"},
    ],
    "data_classes": [
        {"name": "TCKN", "sensitivity": "high"},
        {"name": "gelir", "sensitivity": "high"},
        {"name": "biyometrik", "sensitivity": "high"},
        {"name": "belge", "sensitivity": "high"},
    ],
    "roles": [
        {"name": "Müşteri"},
        {"name": "Kredi politikası ekibi"},
        {"name": "Çağrı merkezi temsilcisi"},
        {"name": "Analitik ekibi"},
    ],
    "assumptions": [],
    "unknowns": [
        {"text": "Belge saklama süresi belirtilmemiş."},
        {"text": "Selfie ve biyometrik verinin silinme koşulları belirtilmemiş."},
        {"text": "Log maskeleme politikası yalnızca kısmen belirtilmiş."},
    ],
}
