"""STRIDE and LINDDUN: the vocabulary the whole platform uses."""

from __future__ import annotations

from scripts.kb_data import entry

STRIDE_LICENSE = "Kendi özetimiz (yöntem kamuya açıktır)"
LINDDUN_LICENSE = "Kendi özetimiz (LINDDUN CC BY 4.0)"

STRIDE = [
    entry(
        "stride",
        "STRIDE-S",
        "Spoofing — Kimlik taklidi",
        """Saldırganın başka bir kullanıcı, servis veya cihaz gibi görünmesi.
        Zayıf kimlik doğrulama, çalınabilir oturum anahtarları, doğrulanmayan
        webhook imzaları, cihaza bağlı olmayan uzun ömürlü token'lar ve SMS
        tabanlı OTP'nin SIM değiştirme saldırısına açık olması tipik
        örneklerdir. Karşı önlem ailesi: güçlü ve çok faktörlü kimlik
        doğrulama, karşılıklı TLS, imza doğrulama, token bağlama.""",
        license=STRIDE_LICENSE,
        url="https://learn.microsoft.com/azure/security/develop/threat-modeling-tool-threats",
        tags=["kimlik", "oturum", "token", "otp", "webhook"],
    ),
    entry(
        "stride",
        "STRIDE-T",
        "Tampering — Veri veya kod değiştirme",
        """Verinin iletim ya da saklama sırasında yetkisiz değiştirilmesi.
        Şifrelenmemiş iç ağ trafiği, imzalanmamış model/yapılandırma
        dosyaları, istemciden gelen ve sunucuda doğrulanmayan parametreler,
        yarış durumları bu başlığa girer. Karşı önlem ailesi: uçtan uca
        şifreleme, bütünlük imzaları, sunucu tarafı doğrulama, idempotency
        anahtarları.""",
        license=STRIDE_LICENSE,
        url="https://learn.microsoft.com/azure/security/develop/threat-modeling-tool-threats",
        tags=["bütünlük", "şifreleme", "doğrulama", "yarış durumu"],
    ),
    entry(
        "stride",
        "STRIDE-R",
        "Repudiation — İnkâr",
        """Bir işlemi kimin yaptığının kanıtlanamaması. Ortak kullanılan
        yönetici hesapları, kaydedilmeyen kritik değişiklikler, imzasız ödeme
        talimatları ve açıklanamayan otomatik kararlar bu başlıktadır. Karşı
        önlem ailesi: kişiye özel hesaplar, değiştirilemez denetim izi,
        dijital imza, karar gerekçesinin saklanması.""",
        license=STRIDE_LICENSE,
        url="https://learn.microsoft.com/azure/security/develop/threat-modeling-tool-threats",
        tags=["denetim izi", "log", "imza", "yönetici paneli"],
    ),
    entry(
        "stride",
        "STRIDE-I",
        "Information disclosure — Bilgi sızması",
        """Hassas verinin yetkisiz kişilere açılması. Loglara yazılan istek
        gövdeleri ve token'lar, maskelenmemiş TCKN/IBAN, şifresiz yedekler,
        uzun ömürlü imzalı URL'ler, gerçek veri içeren test ortamları tipik
        örneklerdir. Karşı önlem ailesi: maskeleme, en az yetki, saklama
        süresi, şifreleme, log hijyeni.""",
        license=STRIDE_LICENSE,
        url="https://learn.microsoft.com/azure/security/develop/threat-modeling-tool-threats",
        tags=["pii", "log", "maskeleme", "yedek", "sızıntı"],
    ),
    entry(
        "stride",
        "STRIDE-D",
        "Denial of service — Hizmet kesintisi",
        """Sistemin meşru kullanıcılara hizmet veremez hâle gelmesi. İstek
        sınırı olmayan uçlar, istemciden alınan sayfalama limitleri, pahalı
        üçüncü taraf sorgularını tetikleyen açık uçlar ve tek noktaya bağlı
        senkron çağrılar bu başlıktadır. Karşı önlem ailesi: hız sınırlama,
        kota, devre kesici, kuyruk ve geri basınç.""",
        license=STRIDE_LICENSE,
        url="https://learn.microsoft.com/azure/security/develop/threat-modeling-tool-threats",
        tags=["hız sınırı", "kota", "dos", "maliyet"],
    ),
    entry(
        "stride",
        "STRIDE-E",
        "Elevation of privilege — Yetki yükseltme",
        """Saldırganın sahip olmadığı yetkileri elde etmesi. Nesne düzeyi
        yetki kontrolü eksikliği (BOLA/IDOR), fonksiyon düzeyi yetki
        eksikliği, aşırı geniş rıza kapsamı, tek kişinin onayıyla canlıya
        çıkan kural değişiklikleri bu başlıktadır. Karşı önlem ailesi: nesne
        sahipliği kontrolü, rol tabanlı yetkilendirme, çift onay, en az
        yetki.""",
        license=STRIDE_LICENSE,
        url="https://learn.microsoft.com/azure/security/develop/threat-modeling-tool-threats",
        tags=["yetki", "bola", "idor", "rbac", "çift onay"],
    ),
]

LINDDUN = [
    entry(
        "linddun",
        "LINDDUN-L",
        "Linkability — İlişkilendirilebilirlik",
        """Farklı kayıtların aynı kişiye ait olduğunun anlaşılabilmesi.
        Sıralı başvuru numaraları, sabit cihaz kimlikleri ve maskelenmemiş
        ortak anahtarlar bunu kolaylaştırır.""",
        license=LINDDUN_LICENSE,
        url="https://linddun.org/",
        tags=["gizlilik", "pii"],
    ),
    entry(
        "linddun",
        "LINDDUN-I",
        "Identifiability — Tanımlanabilirlik",
        """Anonim sanılan verinin kişiye geri bağlanabilmesi. Yetersiz
        maskeleme ve küçük veri kümelerinde birleştirme saldırıları tipik
        nedenlerdir.""",
        license=LINDDUN_LICENSE,
        url="https://linddun.org/",
        tags=["gizlilik", "maskeleme"],
    ),
    entry(
        "linddun",
        "LINDDUN-N",
        "Non-repudiation (gizlilik açısından)",
        """Kişinin bir eylemi yaptığını inkâr edememesi; güvenlik açısından
        istenen bu özellik, gizlilik açısından kişiyi ifşa edebilir.""",
        license=LINDDUN_LICENSE,
        url="https://linddun.org/",
        tags=["gizlilik"],
    ),
    entry(
        "linddun",
        "LINDDUN-D",
        "Detectability — Saptanabilirlik",
        """Bir kaydın var olduğunun, içeriği görülmeden anlaşılabilmesi.
        Örnek: hata mesajından müşterinin bankada hesabı olduğunun
        çıkarılabilmesi.""",
        license=LINDDUN_LICENSE,
        url="https://linddun.org/",
        tags=["gizlilik", "hata mesajı"],
    ),
    entry(
        "linddun",
        "LINDDUN-DD",
        "Disclosure of information — Bilgi ifşası",
        """Kişisel verinin yetkisiz taraflara açılması; KVKK açısından en
        doğrudan karşılığı olan başlıktır.""",
        license=LINDDUN_LICENSE,
        url="https://linddun.org/",
        tags=["gizlilik", "kvkk", "pii"],
    ),
    entry(
        "linddun",
        "LINDDUN-U",
        "Unawareness — Farkında olmama",
        """Kişinin verisinin nasıl işlendiğini bilmemesi. Varsayılan olarak
        işaretli rıza kutuları ve anlaşılmaz aydınlatma metinleri örnektir.""",
        license=LINDDUN_LICENSE,
        url="https://linddun.org/",
        tags=["gizlilik", "rıza"],
    ),
    entry(
        "linddun",
        "LINDDUN-NC",
        "Non-compliance — Uyumsuzluk",
        """Veri işlemenin mevzuata veya kurum politikasına aykırı olması:
        saklama süresinin aşılması, yurt dışına izinsiz aktarım gibi.""",
        license=LINDDUN_LICENSE,
        url="https://linddun.org/",
        tags=["gizlilik", "kvkk", "saklama", "yurt dışı aktarım"],
    ),
]

ENTRIES = STRIDE + LINDDUN
