"""Control frameworks.

Copyrighted standards (ISO/IEC 27001, PCI DSS) are never reproduced here.
ISO entries carry the clause identifier and our own summary only, and every
one is marked ``verification: needed`` because the clause text is behind a
paywall and we cannot confirm the wording from the source. The expert checks
the mapping against the organisation's own copy of the standard before a
report goes out.
"""

from __future__ import annotations

from scripts.kb_data import entry

ISO_LICENSE = "ISO/IEC 27001:2022 · telifli · yalnızca madde kimliği + kendi özetimiz"
NIST_LICENSE = "NIST SP 800-53 Rev. 5 · ABD kamu malı"
ASVS_LICENSE = "OWASP ASVS · CC BY-SA 4.0 · özet bu projede yazılmıştır"
TR_LICENSE = "Türkiye mevzuatı · yalnızca başlık ve bağlantı künyesi"

ISO_URL = "https://www.iso.org/standard/27001"
NIST_URL = "https://csrc.nist.gov/projects/risk-management/sp800-53-controls"


def iso(clause: str, title: str, text: str, tags: list[str]):
    return entry(
        "iso27001",
        clause,
        title,
        text,
        license=ISO_LICENSE,
        url=ISO_URL,
        tags=tags,
        # Clause numbers must be checked against the organisation's own copy.
        verification="needed",
    )


def nist(control: str, title: str, text: str, tags: list[str]):
    return entry(
        "nist80053", control, title, text, license=NIST_LICENSE, url=NIST_URL, tags=tags
    )


def asvs(chapter: str, title: str, text: str, tags: list[str]):
    return entry(
        "asvs",
        chapter,
        title,
        text,
        license=ASVS_LICENSE,
        url="https://owasp.org/www-project-application-security-verification-standard/",
        tags=tags,
    )


ISO = [
    iso("A.5.15", "Erişim denetimi",
        "Kimin neye erişebileceğinin iş gereksinimine göre tanımlanması ve uygulanması.",
        ["yetki", "erişim"]),
    iso("A.5.16", "Kimlik yönetimi",
        "Kullanıcı ve servis kimliklerinin yaşam döngüsünün yönetilmesi; ortak hesap kullanımının engellenmesi.",
        ["kimlik", "ortak hesap"]),
    iso("A.5.17", "Kimlik doğrulama bilgisi",
        "Parola, anahtar ve tek kullanımlık kodların güvenli üretimi, dağıtımı ve saklanması.",
        ["parola", "otp", "anahtar"]),
    iso("A.5.18", "Erişim hakları",
        "Erişim haklarının verilmesi, düzenli gözden geçirilmesi ve ayrılışta kaldırılması.",
        ["yetki", "gözden geçirme"]),
    iso("A.5.19", "Tedarikçi ilişkilerinde bilgi güvenliği",
        "Üçüncü taraf sağlayıcılarla güvenlik gereksinimlerinin sözleşmeye bağlanması.",
        ["üçüncü taraf", "tedarikçi", "sözleşme"]),
    iso("A.5.23", "Bulut hizmetlerinin kullanımında bilgi güvenliği",
        "Bulut ve SaaS kullanımında sorumluluk paylaşımının ve veri konumunun belirlenmesi.",
        ["bulut", "saas", "veri konumu"]),
    iso("A.5.33", "Kayıtların korunması",
        "İşlem kayıtlarının bütünlüğünün ve saklama süresinin korunması.",
        ["kayıt", "saklama", "denetim izi"]),
    iso("A.5.34", "Kişisel verinin gizliliği ve korunması",
        "Kişisel verinin mevzuata uygun işlenmesi ve korunması.",
        ["kvkk", "pii", "gizlilik"]),
    iso("A.8.2", "Ayrıcalıklı erişim hakları",
        "Yönetici ve ayrıcalıklı hesapların sınırlanması, ayrı tutulması ve izlenmesi.",
        ["yönetici", "ayrıcalıklı erişim"]),
    iso("A.8.3", "Bilgiye erişimin kısıtlanması",
        "Hassas alanlara erişimin en az yetki ilkesine göre sınırlanması, maskeleme dahil.",
        ["en az yetki", "maskeleme", "panel"]),
    iso("A.8.5", "Güvenli kimlik doğrulama",
        "Riskle orantılı kimlik doğrulama; kritik işlemlerde çok faktörlü doğrulama.",
        ["mfa", "kimlik doğrulama"]),
    iso("A.8.6", "Kapasite yönetimi",
        "Kaynakların izlenmesi ve yük artışına karşı planlanması.",
        ["kapasite", "dos"]),
    iso("A.8.7", "Zararlı yazılıma karşı koruma",
        "Yüklenen dosyaların taranması ve zararlı yazılım korumasının işletilmesi.",
        ["virüs taraması", "dosya yükleme"]),
    iso("A.8.8", "Teknik açıklıkların yönetimi",
        "Bileşen envanteri, açıklık takibi ve yama süreci.",
        ["yama", "bağımlılık"]),
    iso("A.8.9", "Yapılandırma yönetimi",
        "Güvenli yapılandırmanın tanımlanması ve sapmaların tespiti.",
        ["yapılandırma"]),
    iso("A.8.10", "Bilginin silinmesi",
        "Saklama süresi dolan verinin güvenli biçimde silinmesi.",
        ["saklama süresi", "silme", "kvkk"]),
    iso("A.8.11", "Veri maskeleme",
        "Gerekmeyen yerlerde kişisel verinin maskelenmesi veya takma adlandırılması.",
        ["maskeleme", "tckn", "pii"]),
    iso("A.8.12", "Veri sızıntısının önlenmesi",
        "Toplu veri çıkışının izlenmesi ve engellenmesi.",
        ["sızıntı", "veri ambarı"]),
    iso("A.8.13", "Bilgi yedekleme",
        "Yedeklerin alınması, şifrelenmesi ve geri dönüş testlerinin yapılması.",
        ["yedek", "şifreleme"]),
    iso("A.8.15", "Günlükleme",
        "Olayların kaydedilmesi; kayıtlarda hassas veri bulunmaması.",
        ["log", "maskeleme"]),
    iso("A.8.16", "İzleme faaliyetleri",
        "Anormal davranışın izlenmesi ve alarm üretilmesi.",
        ["izleme", "alarm"]),
    iso("A.8.20", "Ağ güvenliği",
        "Ağların segmentlere ayrılması ve trafiğin korunması.",
        ["ağ", "segmentasyon", "iç ağ"]),
    iso("A.8.21", "Ağ hizmetlerinin güvenliği",
        "Hizmet seviyelerinin ve güvenlik özelliklerinin tanımlanması.",
        ["ağ"]),
    iso("A.8.24", "Kriptografinin kullanımı",
        "Şifreleme ve anahtar yönetimi kurallarının tanımlanması ve uygulanması.",
        ["şifreleme", "anahtar yönetimi", "tls"]),
    iso("A.8.25", "Güvenli geliştirme yaşam döngüsü",
        "Güvenliğin tasarımdan itibaren süreçte yer alması.",
        ["sdlc", "tehdit modelleme"]),
    iso("A.8.26", "Uygulama güvenliği gereksinimleri",
        "Uygulama için güvenlik gereksinimlerinin yazılı hâle getirilmesi.",
        ["gereksinim", "uygulama"]),
    iso("A.8.28", "Güvenli kodlama",
        "Güvenli kodlama kurallarının uygulanması ve gözden geçirilmesi.",
        ["kodlama", "kod incelemesi"]),
    iso("A.8.29", "Geliştirme ve kabulde güvenlik testi",
        "Canlıya çıkmadan önce güvenlik testlerinin yapılması.",
        ["test", "kabul"]),
    iso("A.8.31", "Geliştirme, test ve üretim ortamlarının ayrılması",
        "Ortamların ayrılması ve test ortamlarında gerçek veri kullanılmaması.",
        ["ortam ayrımı", "sandbox", "test verisi"]),
    iso("A.8.32", "Değişiklik yönetimi",
        "Değişikliklerin onaylanması, kaydedilmesi ve geri alınabilir olması.",
        ["değişiklik", "çift onay", "kural değişikliği"]),
]

NIST = [
    nist("AC-2", "Hesap yönetimi",
        "Hesapların açılması, izlenmesi ve kapatılması; ortak hesapların sınırlanması.",
        ["hesap", "ortak hesap"]),
    nist("AC-3", "Erişimin uygulanması",
        "Yetkilendirme kararlarının sistem tarafından zorunlu kılınması.",
        ["yetki"]),
    nist("AC-4", "Bilgi akışının denetlenmesi",
        "Sistemler ve bölgeler arası veri akışının kurallara bağlanması.",
        ["akış", "segmentasyon"]),
    nist("AC-6", "En az yetki",
        "Kullanıcı ve servislere yalnızca gereken yetkinin verilmesi.",
        ["en az yetki"]),
    nist("AC-7", "Başarısız giriş denemeleri",
        "Deneme sayısının sınırlanması ve hesabın kilitlenmesi.",
        ["kaba kuvvet", "otp", "deneme sınırı"]),
    nist("AU-2", "Olay günlüğü",
        "Hangi olayların kaydedileceğinin tanımlanması.",
        ["log"]),
    nist("AU-6", "Kayıtların incelenmesi",
        "Kayıtların düzenli gözden geçirilmesi ve ilişkilendirilmesi.",
        ["log", "izleme"]),
    nist("AU-9", "Denetim bilgisinin korunması",
        "Denetim kayıtlarının değiştirilmeye ve silinmeye karşı korunması.",
        ["denetim izi", "bütünlük"]),
    nist("CM-6", "Yapılandırma ayarları",
        "Güvenli temel yapılandırmanın tanımlanması ve uygulanması.",
        ["yapılandırma", "debug"]),
    nist("CM-7", "Asgari işlevsellik",
        "Yalnızca gerekli servis, port ve uçların açık bırakılması; kullanılmayan yeteneklerin kapatılması.",
        ["envanter", "uç"]),
    nist("CP-9", "Sistem yedekleme",
        "Yedeklerin düzenli alınması, korunması ve geri dönüş testlerinin yapılması.",
        ["yedek"]),
    nist("IA-2", "Kullanıcı kimliğinin doğrulanması",
        "Kullanıcıların benzersiz biçimde tanımlanması ve doğrulanması; ayrıcalıklı erişimde çok faktörlü doğrulama.",
        ["kimlik doğrulama", "mfa"]),
    nist("IA-5", "Kimlik doğrulayıcı yönetimi",
        "Parola, anahtar ve token'ların üretimi, dağıtımı ve yenilenmesi.",
        ["anahtar", "token", "parola"]),
    nist("RA-5", "Açıklık taraması",
        "Düzenli açıklık taraması ve bulguların kapatılması.",
        ["tarama", "açıklık"]),
    nist("SA-11", "Geliştirici testi ve değerlendirmesi",
        "Geliştirme sürecinde güvenlik testlerinin yapılması.",
        ["test", "sdlc"]),
    nist("SC-5", "Hizmet kesintisine karşı koruma",
        "Hız sınırlama ve kaynak kotalarıyla hizmet sürekliliğinin korunması.",
        ["dos", "hız sınırı", "kota"]),
    nist("SC-7", "Sınır koruması",
        "Ağ sınırlarının denetlenmesi; iç kaynaklara giden isteklerin kısıtlanması (SSRF dahil).",
        ["ssrf", "ağ", "sınır"]),
    nist("SC-8", "İletimde gizlilik ve bütünlük",
        "Veri iletiminin şifrelenmesi ve bütünlüğünün korunması; iç ağ dahil.",
        ["tls", "iç ağ", "şifreleme"]),
    nist("SC-13", "Kriptografik koruma",
        "Onaylı kriptografik algoritmaların ve anahtar uzunluklarının kullanılması.",
        ["şifreleme"]),
    nist("SC-28", "Saklanan bilginin korunması",
        "Veritabanı, dosya ve yedeklerde saklanan verinin şifrelenmesi ve anahtarların ayrı yönetilmesi.",
        ["şifreleme", "yedek", "veritabanı"]),
    nist("SI-4", "Sistem izleme",
        "Anormal davranışın tespiti ve alarm üretilmesi.",
        ["izleme", "alarm"]),
    nist("SI-7", "Yazılım ve bilgi bütünlüğü",
        "Dosya ve model bütünlüğünün imza ile doğrulanması.",
        ["bütünlük", "imza", "model"]),
    nist("SI-10", "Girdi doğrulama",
        "Gelen verinin biçim ve içerik açısından doğrulanması.",
        ["girdi doğrulama"]),
    nist("SI-11", "Hata yönetimi",
        "Hata mesajlarının kullanıcıya iç bilgi sızdırmaması; ayrıntının yalnızca logda tutulması.",
        ["hata mesajı"]),
    nist("SR-3", "Tedarik zinciri denetimleri",
        "Tedarik zinciri bileşenlerinin doğrulanması.",
        ["tedarik zinciri"]),
]

ASVS = [
    asvs("ASVS-V1", "Mimari, tasarım ve tehdit modelleme",
        "Güvenlik gereksinimlerinin ve tehdit modelinin tasarımda ele alınması.",
        ["tasarım", "tehdit modelleme"]),
    asvs("ASVS-V2", "Kimlik doğrulama",
        "Parola, çok faktörlü doğrulama, tek kullanımlık kod ve kurtarma akışlarının doğrulanması.",
        ["kimlik doğrulama", "otp", "mfa"]),
    asvs("ASVS-V3", "Oturum yönetimi",
        "Oturum üretimi, yenilenmesi, süresi ve iptali.",
        ["oturum", "token"]),
    asvs("ASVS-V4", "Erişim denetimi",
        "Nesne ve fonksiyon düzeyinde yetkilendirmenin sunucu tarafında doğrulanması.",
        ["yetki", "bola", "idor"]),
    asvs("ASVS-V5", "Doğrulama, temizleme ve kodlama",
        "Girdi doğrulama ve çıktı kodlama ile enjeksiyonun engellenmesi.",
        ["girdi doğrulama", "enjeksiyon"]),
    asvs("ASVS-V6", "Saklanan veride kriptografi",
        "Şifreleme ve anahtar yönetimi gereksinimleri.",
        ["şifreleme", "anahtar"]),
    asvs("ASVS-V7", "Hata yönetimi ve günlükleme",
        "Kayıtların yeterliliği ve hassas veri içermemesi.",
        ["log", "hata mesajı"]),
    asvs("ASVS-V8", "Veri koruma",
        "Hassas verinin asgari toplanması, maskelenmesi ve saklama süresi.",
        ["maskeleme", "saklama", "pii"]),
    asvs("ASVS-V9", "İletişim güvenliği",
        "Tüm iletişimde TLS kullanımı, sertifika doğrulaması ve güvensiz sürümlerin kapatılması.",
        ["tls", "sertifika"]),
    asvs("ASVS-V10", "Zararlı kod",
        "Üçüncü taraf kod, bağımlılık ve yüklenen dosyaların bütünlüğünün ve güvenilirliğinin doğrulanması.",
        ["bütünlük", "bağımlılık"]),
    asvs("ASVS-V11", "İş mantığı",
        "İş akışlarının sıra, hız ve tutarlılık açısından korunması; yarış durumları.",
        ["iş mantığı", "yarış durumu", "limit"]),
    asvs("ASVS-V12", "Dosya ve kaynaklar",
        "Dosya yükleme, tür doğrulama ve güvenli saklama.",
        ["dosya yükleme", "depolama"]),
    asvs("ASVS-V13", "API ve web servisleri",
        "REST/GraphQL uçlarının yetkilendirme, doğrulama ve hız sınırı gereksinimleri.",
        ["api", "hız sınırı"]),
    asvs("ASVS-V14", "Yapılandırma",
        "Üretim yapılandırmasının sertleştirilmesi; hata ayıklamanın kapalı olması.",
        ["yapılandırma", "debug"]),
]

TR = [
    entry("tr_regulation", "BDDK-BSEBH",
        "BDDK Bilgi Sistemleri ve Elektronik Bankacılık Hizmetleri Hakkında Yönetmelik",
        """Bankaların bilgi sistemleri yönetimi, kimlik doğrulama, işlem
        güvenliği, dış hizmet alımı ve denetim izi yükümlülüklerini düzenleyen
        yönetmelik. Bu platform yalnızca künye düzeyinde atıf yapar; madde
        eşlemesi uzman tarafından doğrulanmalıdır.""",
        license=TR_LICENSE,
        url="https://www.mevzuat.gov.tr/",
        tags=["bddk", "bankacılık", "mevzuat", "denetim izi"],
        verification="needed"),
    entry("tr_regulation", "KVKK-6698",
        "6698 sayılı Kişisel Verilerin Korunması Kanunu",
        """Kişisel verinin işlenmesi, aktarılması, saklanması ve silinmesine
        ilişkin yükümlülükler. Yurt dışına aktarım, aydınlatma ve veri
        minimizasyonu bu platformdaki gizlilik bulgularıyla ilişkilidir. Madde
        eşlemesi uzman tarafından doğrulanmalıdır.""",
        license=TR_LICENSE,
        url="https://www.mevzuat.gov.tr/mevzuatmetin/1.5.6698.pdf",
        tags=["kvkk", "pii", "gizlilik", "yurt dışı aktarım", "saklama"],
        verification="needed"),
]

ENTRIES = ISO + NIST + ASVS + TR
