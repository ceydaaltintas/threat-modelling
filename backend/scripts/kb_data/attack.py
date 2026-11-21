"""MITRE ATT&CK (Enterprise + Mobile) and CAPEC subsets.

Only identifiers, public technique names and our own Turkish summaries.
"""

from __future__ import annotations

from scripts.kb_data import entry

ATTACK_LICENSE = "MITRE ATT&CK® · Apache-2.0 · atıf zorunlu · özet bu projede yazılmıştır"
CAPEC_LICENSE = "MITRE CAPEC™ · serbest kullanım, atıf zorunlu · özet bu projede yazılmıştır"


def attack(tid: str, title: str, text: str, tags: list[str], mobile: bool = False):
    path = tid.replace(".", "/")
    return entry(
        "attack_mobile" if mobile else "attack",
        tid,
        title,
        text,
        license=ATTACK_LICENSE,
        url=f"https://attack.mitre.org/techniques/{path}/",
        tags=tags,
    )


def capec(number: str, title: str, text: str, tags: list[str]):
    return entry(
        "capec",
        f"CAPEC-{number}",
        title,
        text,
        license=CAPEC_LICENSE,
        url=f"https://capec.mitre.org/data/definitions/{number}.html",
        tags=tags,
    )


ENTRIES = [
    attack("T1078", "Geçerli hesapların kullanılması",
        """Saldırganın çalınmış meşru kimlik bilgileriyle oturum açması.
        Ortak kullanılan yönetici hesapları ve MFA'sız portallar bunu
        kolaylaştırır.""",
        ["hesap ele geçirme", "yönetici", "mfa"]),
    attack("T1110", "Kaba kuvvet",
        """Parola veya tek kullanımlık kod denemeleriyle hesaba erişim.
        Deneme sınırı olmayan OTP uçları doğrudan hedeftir.""",
        ["kaba kuvvet", "otp", "parola"]),
    attack("T1556", "Kimlik doğrulama sürecinin değiştirilmesi",
        """Kimlik doğrulama akışının veya onu uygulayan bileşenin
        değiştirilerek atlatılması; örneğin kontrolün yalnızca istemcide
        yapılması ya da sunucuda devre dışı bırakılabilmesi.""",
        ["kimlik doğrulama", "atlatma"]),
    attack("T1557", "Araya girme (adversary-in-the-middle)",
        """Trafiğin araya girilerek okunması veya değiştirilmesi; şifresiz iç
        ağ trafiği ve sertifika sabitlemesi olmayan mobil uygulamalar
        hedeftir.""",
        ["mitm", "tls", "iç ağ", "sertifika sabitleme"]),
    attack("T1566", "Oltalama (phishing)",
        """Kullanıcıyı sahte bağlantı veya ek yoluyla kandırma. Tek kullanımlık
        olmayan kampanya bağlantıları ve açık yönlendirme bunu
        güçlendirir.""",
        ["oltalama", "sms", "bağlantı", "yönlendirme"]),
    attack("T1539", "Oturum çerezinin çalınması",
        """Geçerli oturum anahtarının ele geçirilip yeniden kullanılması.""",
        ["oturum", "token", "çerez"]),
    attack("T1552", "Korumasız kimlik bilgileri",
        """Yapılandırma dosyalarında, ortam değişkenlerinde veya kod
        deposunda bulunan anahtarlar.""",
        ["sır", "configmap", "api anahtarı"]),
    attack("T1213", "Bilgi havuzlarından veri toplama",
        """Veri ambarı, wiki ve paylaşımlı klasörlerden toplu veri çekme;
        geniş erişim yetkisi riski büyütür.""",
        ["veri ambarı", "pii", "geniş erişim"]),
    attack("T1530", "Bulut depolamadaki veriye erişim",
        """Nesne depolamadaki belgelere yetkisiz erişim; uzun ömürlü imzalı
        URL'ler tipik zafiyettir.""",
        ["nesne depolama", "imzalı url", "belge"]),
    attack("T1190", "İnternete açık uygulamanın istismarı",
        """İnternete bakan servislerdeki açıklardan yararlanma.""",
        ["internete açık", "api", "web"]),
    attack("T1498", "Ağ hizmet kesintisi",
        """Hedefin ağ bant genişliğini veya bağlantı kapasitesini doldurarak
        hizmetin meşru kullanıcılara verilememesi. İnternete açık uçlarda hız
        sınırı ve kenar koruması olmaması etkiyi büyütür.""",
        ["dos", "hız sınırı", "internete açık"]),
    attack("T1499", "Uç nokta hizmet kesintisi",
        """Uygulama kaynaklarını tüketerek hizmeti durdurma; pahalı sorgular
        ve büyük sayfalama istekleri.""",
        ["dos", "sayfalama", "kaynak tüketimi"]),
    attack("T1565", "Veri değiştirme",
        """Saklanan veya iletilen verinin değiştirilmesi; imzasız talimatlar
        ve şifresiz iç trafik riski artırır.""",
        ["bütünlük", "veri değiştirme"]),
    attack("T1070", "Göstergelerin silinmesi",
        """Saldırganın log kayıtlarını silerek veya değiştirerek izlerini yok
        etmesi; yalnızca eklenebilir (append-only) ve ayrı tutulan denetim izi
        bunu engeller.""",
        ["log", "denetim izi", "bütünlük"]),
    attack("T1195", "Tedarik zinciri saldırısı",
        """Bağımlılık, model dosyası veya güncelleme kanalının ele
        geçirilmesi.""",
        ["tedarik zinciri", "bağımlılık", "model"]),
    attack("T1199", "Güvenilen ilişkinin istismarı",
        """Üçüncü taraf entegrasyonunun kötüye kullanılması; TPP, SMS
        operatörü, KYC sağlayıcısı gibi.""",
        ["üçüncü taraf", "tpp", "entegrasyon"]),
    attack("T1496", "Kaynak gaspı",
        """Hesap veya altyapı kaynaklarının saldırgan yararına
        kullanılması; ücretli dış sorguların tetiklenmesi dahil.""",
        ["maliyet", "kota"]),
    attack("T1621", "Çok faktörlü kimlik doğrulama isteği üretme",
        """Kullanıcıyı onay vermeye zorlamak için arka arkaya MFA isteği
        göndermek.""",
        ["mfa", "otp", "sosyal mühendislik"]),
    attack("T1111", "Çok faktörlü kimlik doğrulamanın ele geçirilmesi",
        """SMS OTP'nin yönlendirilmesi veya SIM değiştirme ile alınması.""",
        ["otp", "sms", "sim swap"], ),
    attack("T1517", "Mobil: bildirimlere erişim",
        """Zararlı uygulamanın bildirimleri okuyarak OTP kodunu ele
        geçirmesi.""",
        ["mobil", "otp", "bildirim"], mobile=True),
    attack("T1409", "Mobil: uygulama verisine erişim",
        """Root/jailbreak yapılmış cihazda uygulama deposundaki verinin
        okunması.""",
        ["mobil", "root", "jailbreak", "saklama"], mobile=True),
    attack("T1406", "Mobil: gizleme ve paketleme",
        """Zararlı mobil uygulamanın analizden kaçınması; karşı tarafta kod
        karartma eksikliği tersine mühendisliği kolaylaştırır.""",
        ["mobil", "obfuscation", "tersine mühendislik"], mobile=True),
    attack("T1417", "Mobil: girdi yakalama",
        """Sahte ekran veya klavye ile kimlik bilgisi toplama.""",
        ["mobil", "overlay", "kimlik bilgisi"], mobile=True),

    capec("115", "Kimlik doğrulamanın atlatılması",
        """Kimlik doğrulama adımının hiç çalıştırılmadan geçilmesi; iç
        servislerin doğrudan çağrılabilmesi ya da muafiyetlerin
        doğrulanmaması gibi.""",
        ["kimlik doğrulama", "iç servis", "muafiyet"]),
    capec("122", "Yetki suistimali",
        """Sahip olunan yetkinin amacı dışında kullanılması; iç kaynaklı
        sızıntının ana yoludur.""",
        ["iç tehdit", "yetki", "panel"]),
    capec("212", "İşlevselliğin kötüye kullanılması",
        """Sistemin meşru işlevinin, hiçbir açık kullanılmadan saldırgan
        yararına çalıştırılması; limit, kampanya ve iade akışları tipik
        hedeflerdir.""",
        ["iş mantığı", "limit", "kampanya"]),
    capec("233", "Yetki yükseltme",
        """Düşük yetkili bir hesaptan daha yüksek yetkiye geçilmesi; eksik
        fonksiyon düzeyi kontrol ve aşırı geniş rol tanımları tipik
        nedenlerdir.""",
        ["yetki", "rbac"]),
    capec("242", "Kod enjeksiyonu",
        """Çalıştırılacak koda veya şablona kullanıcı girdisinin karışması;
        kural motorları ve dinamik şablonlarda görülür.""",
        ["enjeksiyon", "kural motoru"]),
    capec("310", "Altyapı taraması",
        """Hedef sistemin uçlarının ve sürümlerinin keşfi; belgelenmemiş
        uçlar burada ortaya çıkar.""",
        ["keşif", "envanter"]),
    capec("593", "Oturum ele geçirme",
        """Geçerli bir oturumun devralınması; çalınan token veya çerezin
        yeniden kullanılmasıyla gerçekleşir.""",
        ["oturum", "token", "çerez"]),
    capec("664", "Sunucu taraflı istek sahteciliği",
        """Sunucuya, saldırganın belirlediği adrese istek yaptırma.""",
        ["ssrf", "webhook"]),
]
