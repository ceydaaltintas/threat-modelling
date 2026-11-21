"""Hand-built system model for sample document 3 (OB-PLT-SA-001)."""

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


OPEN_BANKING_MODEL = {
    "components": [
        _c("tpp-uygulamalari", "TPP Uygulamaları", "external",
           "Firmaya özgü, tpp", "İnternet (dış)", True,
           "Lisanslı dış firmaların web ve mobil uygulamaları."),
        _c("gelistirici-portali", "Geliştirici Portalı", "web_app",
           "Web uygulaması, portal, api anahtarı, e-posta", "DMZ", True,
           "TPP kaydı, uygulama tanımı, API anahtarı alma ve sandbox erişimi."),
        _c("api-gecidi", "API Geçidi", "gateway",
           "Kong, OAuth2, mTLS, sertifika, hız sınırlama", "DMZ", True,
           "OAuth2 token doğrulama, karşılıklı TLS (mTLS), hız sınırlama."),
        _c("yetkilendirme", "Yetkilendirme Sunucusu", "auth",
           "Keycloak, oauth, openid, redirect, yetkilendirme, token, "
           "yenileme, jwt", "Uygulama", True,
           "OAuth2/OIDC: Authorization Code + PKCE; erişim ve yenileme "
           "token'ları.",
           auth="OAuth2 / OIDC"),
        _c("riza-servisi", "Rıza Yönetim Servisi", "service",
           "Java, PostgreSQL, rıza, consent, izin", "Uygulama", False,
           "Müşteri rızasının kapsamı, süresi ve hesapları; rıza iptali."),
        _c("hesap-bilgisi", "Hesap Bilgisi Servisi", "api",
           "Java, Spring Boot", "Uygulama", False,
           "Bakiye ve hesap hareketlerini sunar."),
        _c("odeme-baslatma", "Ödeme Başlatma Servisi", "api",
           "Java, Spring Boot, ödeme başlatma, talimat, sca, muafiyet, tpp",
           "Uygulama", False,
           "TPP'nin ilettiği ödeme talimatını işler; durumunu takip eder."),
        _c("musteri-onay", "Müşteri Onay Uygulaması", "mobile_app",
           "iOS/Android, rıza, SCA", "İnternet (müşteri cihazı)", True,
           "Banka mobil uygulaması: rıza ekranı ve güçlü müşteri doğrulama "
           "(SCA)."),
        _c("sertifika-deposu", "TPP Sertifika Deposu", "admin",
           "Java, PostgreSQL, sertifika, tpp, onay", "Uygulama (yönetim)",
           False,
           "TPP sertifikalarının yüklendiği, yönetici onayıyla "
           "etkinleştirildiği depo."),
        _c("webhook-servisi", "Webhook Servisi", "service",
           "Java, webhook, callback, bildirim", "Uygulama", False,
           "Ödeme durumu değişince TPP'nin kayıtlı callback URL'sine bildirim "
           "gönderir."),
        _c("sandbox", "Sandbox Ortamı", "service",
           "Kubernetes, sandbox, test", "Ayrı ortam", True,
           "TPP'lerin test için kullandığı ortam."),
        _c("cekirdek", "Çekirdek Bankacılık", "external",
           "Mainframe", "Çekirdek", False,
           "Hesap ve işlem verisinin ana sistemi."),
        _c("log-platformu", "API İstek Logları", "other",
           "log, izleme, token", "Uygulama", False,
           "Tanılama amacıyla erişim token'ları API istek loglarında "
           "saklanır."),
    ],
    "data_flows": [
        {
            "id": "f-tpp-gecit", "source_id": "tpp-uygulamalari",
            "target_id": "api-gecidi", "protocol": "HTTPS, mTLS",
            "encrypted": True, "authenticated": True,
            "data_classes": ["hesap bilgisi", "IBAN", "bakiye"],
            "evidence": [{"quote": "OAuth2 token doğrulama, karşılıklı TLS "
                                   "(mTLS), hız sınırlama.", "page": 1}],
        },
        {
            "id": "f-gecit-hesap", "source_id": "api-gecidi",
            "target_id": "hesap-bilgisi", "protocol": "HTTPS, mTLS",
            "encrypted": True, "authenticated": True,
            "data_classes": ["hesap bilgisi", "bakiye"],
            "evidence": [{"quote": "servisler arası iletişimde karşılıklı TLS "
                                   "kullanılır", "page": 2}],
        },
        {
            "id": "f-gecit-odeme", "source_id": "api-gecidi",
            "target_id": "odeme-baslatma", "protocol": "HTTPS, mTLS",
            "encrypted": True, "authenticated": True,
            "data_classes": ["tutar", "IBAN"],
            "evidence": [{"quote": "TPP, ödeme talimatını Ödeme Başlatma "
                                   "Servisi'ne iletir.", "page": 2}],
        },
        {
            "id": "f-webhook-tpp", "source_id": "webhook-servisi",
            "target_id": "tpp-uygulamalari", "protocol": "HTTPS POST",
            "encrypted": True, "authenticated": "unknown",
            "data_classes": ["ödeme durumu"],
            "evidence": [{"quote": "URL doğrulaması yalnızca https şemasını "
                                   "kontrol eder.", "page": 2}],
        },
        {
            "id": "f-yetki-riza", "source_id": "yetkilendirme",
            "target_id": "riza-servisi", "protocol": "HTTPS",
            "encrypted": True, "authenticated": True,
            "data_classes": ["rıza", "hesap bilgisi"],
            "evidence": [{"quote": "Müşteri rızasının kapsamı, süresi ve "
                                   "hesapları; rıza iptali.", "page": 1}],
        },
        {
            "id": "f-hesap-cekirdek", "source_id": "hesap-bilgisi",
            "target_id": "cekirdek", "protocol": "mainframe",
            "encrypted": "unknown", "authenticated": "unknown",
            "data_classes": ["hesap bilgisi", "IBAN", "bakiye"],
            "evidence": [],
        },
        {
            "id": "f-gecit-log", "source_id": "api-gecidi",
            "target_id": "log-platformu", "protocol": "log",
            "encrypted": "unknown", "authenticated": "unknown",
            "data_classes": ["token", "kimlik bilgisi"],
            "evidence": [{"quote": "erişim token'ları API istek loglarında "
                                   "saklanır", "page": 2}],
        },
        {
            "id": "f-sandbox-cekirdek", "source_id": "cekirdek",
            "target_id": "sandbox", "protocol": "kopya",
            "encrypted": "unknown", "authenticated": "unknown",
            "data_classes": ["IBAN", "bakiye"],
            "evidence": [{"quote": "Sandbox Ortamı, üretim verisinin kopyasıyla "
                                   "beslenir", "page": 2}],
        },
    ],
    "trust_zones": [
        {"id": "internet-dis", "name": "İnternet (dış)"},
        {"id": "dmz", "name": "DMZ"},
        {"id": "uygulama", "name": "Uygulama"},
        {"id": "yonetim", "name": "Uygulama (yönetim)"},
        {"id": "ayri-ortam", "name": "Ayrı ortam"},
        {"id": "cekirdek", "name": "Çekirdek"},
    ],
    "data_classes": [
        {"name": "IBAN", "sensitivity": "high"},
        {"name": "bakiye", "sensitivity": "high"},
        {"name": "hesap bilgisi", "sensitivity": "high"},
        {"name": "token", "sensitivity": "high"},
    ],
    "roles": [
        {"name": "TPP"},
        {"name": "Müşteri"},
        {"name": "Yönetici"},
        {"name": "Geliştirme ve destek ekipleri"},
    ],
    "assumptions": [],
    "unknowns": [
        {"text": "redirect_uri için tam eşleşme doğrulamasına geçiş "
                 "planlanıyor ama uygulanmamış."},
        {"text": "Webhook hedef adreslerinin iç ağ adreslerini dışlayacak "
                 "şekilde doğrulanması açık konu."},
        {"text": "Sandbox verisinin tamamen sentetik hale getirilmesi açık "
                 "konu."},
    ],
}
