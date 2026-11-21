"""CWE subset relevant to banking web, API, mobile and data platforms."""

from __future__ import annotations

from scripts.kb_data import entry

CWE_LICENSE = "MITRE CWE · serbest kullanım, atıf zorunlu · özet bu projede yazılmıştır"


def cwe(number: str, title: str, text: str, tags: list[str]):
    return entry(
        "cwe",
        f"CWE-{number}",
        title,
        text,
        license=CWE_LICENSE,
        url=f"https://cwe.mitre.org/data/definitions/{number}.html",
        tags=tags,
    )


ENTRIES = [
    cwe("20", "Yetersiz girdi doğrulama",
        """Gelen verinin tür, uzunluk, biçim ve aralık açısından
        doğrulanmaması. Sonraki tüm enjeksiyon ve iş mantığı hatalarının
        zeminini hazırlar.""",
        ["girdi doğrulama", "api", "web"]),
    cwe("22", "Dizin aşımı (path traversal)",
        """Dosya adının kullanıcıdan alınıp doğrulanmadan yol olarak
        kullanılması; belge yükleme ve indirme uçlarında görülür.""",
        ["dosya yükleme", "depolama"]),
    cwe("79", "Siteler arası betik çalıştırma (XSS)",
        """Kullanıcı girdisinin kaçışsız olarak HTML'e yazılması; oturum
        çalma ve sahte işlem başlatma riski.""",
        ["web", "xss", "tarayıcı"]),
    cwe("89", "SQL enjeksiyonu",
        """Girdinin SQL sorgusuna doğrudan gömülmesi. Parametreli sorgu ve
        ORM kullanımı, en az yetkili veritabanı kullanıcısı temel
        önlemlerdir. Bankacılıkta veri sızıntısı ve veri değiştirme için en
        doğrudan yoldur.""",
        ["sql", "veritabanı", "enjeksiyon"]),
    cwe("78", "İşletim sistemi komut enjeksiyonu",
        """Girdinin kabuk komutuna gömülmesi; dosya dönüştürme ve OCR gibi
        dış araç çağıran servislerde risklidir.""",
        ["komut enjeksiyonu", "ocr", "dosya işleme"]),
    cwe("94", "Kod enjeksiyonu",
        """Dinamik olarak çalıştırılan koda girdi karışması; kural motoru ve
        şablon motorlarında görülür.""",
        ["kural motoru", "şablon"]),
    cwe("200", "Hassas bilginin yetkisiz kişiye açılması",
        """Yanıtlarda, hata mesajlarında veya loglarda gereğinden fazla veri
        dönmesi.""",
        ["bilgi sızması", "log", "hata mesajı"]),
    cwe("209", "Hata mesajıyla bilgi sızması",
        """Yığın izi, sorgu metni veya iç adreslerin kullanıcıya
        gösterilmesi.""",
        ["hata mesajı", "bilgi sızması"]),
    cwe("213", "Politikaya aykırı veri açığa çıkarma",
        """Maskelenmesi gereken alanların panellerde ve raporlarda tam
        gösterilmesi; çağrı merkezi ekranlarında TCKN ve gelir bilgisi
        gibi.""",
        ["maskeleme", "pii", "panel", "tckn"]),
    cwe("256", "Kimlik bilgisinin korumasız saklanması",
        """Parola ve anahtarların düz metin olarak yapılandırmada, kodda veya
        ConfigMap'te tutulması.""",
        ["anahtar yönetimi", "configmap", "sır"]),
    cwe("285", "Yetersiz yetkilendirme",
        """Kimliği doğrulanmış kullanıcının yapabileceklerinin sunucu
        tarafında sınırlanmaması.""",
        ["yetki", "rbac"]),
    cwe("287", "Yetersiz kimlik doğrulama",
        """Kimliğin zayıf veya atlatılabilir biçimde doğrulanması.""",
        ["kimlik doğrulama", "oturum"]),
    cwe("306", "Kritik işlev için kimlik doğrulama eksikliği",
        """Yönetim veya iç servis uçlarının kimlik doğrulamasız açık
        olması.""",
        ["iç servis", "yönetim paneli", "api"]),
    cwe("307", "Deneme sayısının sınırlanmaması",
        """Giriş veya OTP uçlarında kaba kuvvet denemesine sınır konmaması.
        Altı haneli bir OTP, sınırsız denemede kısa sürede bulunabilir.""",
        ["otp", "kaba kuvvet", "hız sınırı", "kimlik doğrulama"]),
    cwe("311", "Hassas verinin şifrelenmemesi",
        """Verinin iletimde veya saklamada açık kalması; iç ağda HTTP,
        şifresiz yedek.""",
        ["şifreleme", "tls", "yedek"]),
    cwe("319", "Hassas bilginin şifresiz iletilmesi",
        """İç ağ dahil olmak üzere düz metin protokol kullanımı; araya girme
        ile okuma ve değiştirme riski.""",
        ["tls", "iç ağ", "mitm", "http"]),
    cwe("327", "Zayıf veya hatalı kriptografi kullanımı",
        """Eskimiş algoritmalar, hatalı mod seçimi, sabit başlatma vektörü.""",
        ["şifreleme", "algoritma"]),
    cwe("352", "Siteler arası istek sahteciliği (CSRF)",
        """Kullanıcının oturumuyla, haberi olmadan işlem yaptırılması.""",
        ["web", "csrf", "oturum"]),
    cwe("362", "Yarış durumu (race condition)",
        """Eşzamanlı isteklerin paylaşılan durumu bozması; sayaç işlemden
        sonra güncelleniyorsa günlük limit aşılabilir.""",
        ["yarış durumu", "limit", "sayaç", "eşzamanlılık"]),
    cwe("384", "Oturum sabitleme",
        """Girişten önce verilen oturum kimliğinin giriş sonrası
        yenilenmemesi.""",
        ["oturum"]),
    cwe("400", "Denetimsiz kaynak tüketimi",
        """İstek, bellek veya maliyet sınırı olmaması; pahalı dış sorguları
        tetikleyen uçlar.""",
        ["dos", "hız sınırı", "maliyet", "kota"]),
    cwe("434", "Tehlikeli dosya türünün sınırsız yüklenmesi",
        """Yalnızca uzantıya bakarak dosya kabul etmek; içerik doğrulaması ve
        zararlı yazılım taraması yapılmaması.""",
        ["dosya yükleme", "belge", "virüs taraması"]),
    cwe("502", "Güvensiz serileştirme",
        """Güvenilmeyen kaynaktan gelen nesnenin doğrudan çözülmesi.""",
        ["serileştirme", "kuyruk"]),
    cwe("522", "Yetersiz korunan kimlik bilgileri",
        """Kimlik bilgisinin zayıf korunması, e-posta gibi güvensiz kanalla
        iletilmesi.""",
        ["api anahtarı", "e-posta", "portal"]),
    cwe("523", "Kimlik bilgisinin korumasız iletilmesi",
        """Anahtar veya parolanın şifresiz kanaldan gönderilmesi.""",
        ["api anahtarı", "iletim"]),
    cwe("532", "Loglara hassas bilgi yazılması",
        """İstek/yanıt gövdelerinin, token'ların, IBAN ve tutar bilgisinin
        log'a düşmesi; üretimde DEBUG seviyesi en sık nedendir.""",
        ["log", "debug", "token", "iban", "pii"]),
    cwe("539", "Kalıcı çerezde hassas bilgi",
        """Oturum veya kimlik bilgisinin uzun ömürlü çerezde tutulması.""",
        ["çerez", "oturum", "web"]),
    cwe("565", "İstemciden gelen değere güvenme",
        """Fiyat, limit, sayfa boyutu gibi değerlerin istemciden alınıp
        doğrulanmaması.""",
        ["api", "iş mantığı", "sayfalama"]),
    cwe("598", "Hassas verinin URL sorgu dizesinde taşınması",
        """Token veya kişisel verinin URL'de yer alması; log ve referrer
        üzerinden sızar.""",
        ["url", "token", "log"]),
    cwe("601", "Açık yönlendirme",
        """Yönlendirme adresinin yeterince doğrulanmaması; OAuth
        redirect_uri'nin ön ek eşleşmesiyle kabul edilmesi saldırgana
        yetkilendirme kodunu taşıyabilir.""",
        ["oauth", "redirect_uri", "yönlendirme"]),
    cwe("613", "Yetersiz oturum süresi yönetimi",
        """Token ömrünün uzun olması, iptal edilememesi, cihazla
        ilişkilendirilmemesi.""",
        ["oturum", "token", "jwt"]),
    cwe("639", "Anahtar değiştirerek yetki aşımı (IDOR)",
        """Kaynak kimliğini değiştirerek başkasının kaydına erişmek; sıralı
        kimlikler riski büyütür.""",
        ["idor", "bola", "api", "başvuru numarası"]),
    cwe("640", "Parola kurtarma mekanizmasının zayıflığı",
        """Tek kullanımlık olmayan, uzun süre geçerli sıfırlama
        bağlantıları.""",
        ["parola sıfırlama", "bağlantı", "sms"]),
    cwe("770", "Kota veya azaltma olmadan kaynak ayırma",
        """İstek başına bellek, bağlantı veya işlem sınırı konmaması; tek bir
        istemci sistemin kaynaklarını tüketebilir.""",
        ["kota", "dos", "kaynak tüketimi"]),
    cwe("778", "Yetersiz günlükleme",
        """Kritik işlemlerin kaydedilmemesi; inkâr ve soruşturma sorunu.""",
        ["log", "denetim izi", "inkâr"]),
    cwe("799", "Etkileşim sıklığının denetlenmemesi",
        """Otomatik taleplerin engellenmemesi; başvuru seli ve numaralandırma
        saldırıları.""",
        ["hız sınırı", "numaralandırma", "otomasyon"]),
    cwe("862", "Yetkilendirme eksikliği",
        """Bir işlem veya kaynak için yetki kontrolünün hiç yapılmaması;
        kimliği doğrulanmış herkes her şeyi yapabilir.""",
        ["yetki", "erişim denetimi"]),
    cwe("863", "Hatalı yetkilendirme",
        """Yetki kontrolünün yapıldığı ama yanlış kurguladığı durumlar.""",
        ["yetki", "rbac"]),
    cwe("915", "Değiştirilebilir alanların denetimsiz atanması (mass assignment)",
        """İstek gövdesindeki alanların doğrudan nesneye atanması.""",
        ["api", "mass assignment"]),
    cwe("918", "Sunucu taraflı istek sahteciliği (SSRF)",
        """Sunucunun kullanıcıdan gelen adrese istek yapması; iç ağ ve bulut
        meta veri uçlarına erişim.""",
        ["ssrf", "webhook", "callback", "iç ağ"]),
    cwe("1021", "Arayüz katmanının kısıtlanmaması (clickjacking)",
        """Sayfanın başka bir sitede çerçeve içine alınabilmesi; kullanıcı
        farkında olmadan işlem onaylatılabilir.""",
        ["web", "clickjacking", "çerçeve"]),
    cwe("1230", "Yetkisiz hata ayıklama arayüzü",
        """Üretimde açık kalan hata ayıklama uçları.""",
        ["debug", "yapılandırma"]),
    cwe("1392", "Varsayılan kimlik bilgisi kullanımı",
        """Kurulumla gelen hesapların değiştirilmemesi.""",
        ["varsayılan hesap", "yapılandırma"]),
]
