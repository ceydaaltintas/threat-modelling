"""OWASP lists.

Only identifiers, public titles and our own Turkish summaries are stored; the
OWASP text itself is not reproduced. Reader is always pointed at the source.
"""

from __future__ import annotations

from scripts.kb_data import entry

CC = "OWASP · CC BY-SA 4.0 · özet bu projede yazılmıştır"

TOP10 = [
    entry("owasp", "A01:2021", "Bozuk erişim denetimi",
        """Kullanıcının yetkisi olmayan veriye veya işleve erişebilmesi.
        Nesne kimliğini değiştirerek başkasının kaydını görme (IDOR), eksik
        fonksiyon düzeyi kontrol, istemci tarafında yapılan yetki kontrolü bu
        başlığa girer. Bankacılıkta hesap sahipliği doğrulamasının eksik
        olması en kritik örneğidir.""",
        license=CC, url="https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
        tags=["yetki", "idor", "bola", "api", "web"]),
    entry("owasp", "A02:2021", "Kriptografik hatalar",
        """Hassas verinin şifrelenmemesi, zayıf algoritma kullanılması,
        anahtarların kod veya yapılandırma dosyasında tutulması. Şifrelenmemiş
        yedekler, iç ağda düz HTTP ve ConfigMap içinde saklanan API
        anahtarları tipik bulgulardır.""",
        license=CC, url="https://owasp.org/Top10/A02_2021-Cryptographic_Failures/",
        tags=["şifreleme", "tls", "anahtar yönetimi", "yedek"]),
    entry("owasp", "A03:2021", "Enjeksiyon",
        """Kullanıcı girdisinin komut, sorgu veya şablona doğrudan
        gömülmesi: SQL, NoSQL, OS komutu, LDAP, şablon enjeksiyonu. Parametreli
        sorgu ve girdi doğrulaması temel önlemdir.""",
        license=CC, url="https://owasp.org/Top10/A03_2021-Injection/",
        tags=["sql", "enjeksiyon", "veritabanı", "girdi doğrulama"]),
    entry("owasp", "A04:2021", "Güvensiz tasarım",
        """Güvenlik gereksinimlerinin tasarım aşamasında hiç düşünülmemiş
        olması. İş mantığı suistimalleri, eksik limit ve kota tasarımı, tehdit
        modellemesinin yapılmamış olması bu başlıktadır.""",
        license=CC, url="https://owasp.org/Top10/A04_2021-Insecure_Design/",
        tags=["tasarım", "iş mantığı", "limit"]),
    entry("owasp", "A05:2021", "Güvenlik yanlış yapılandırması",
        """Varsayılan hesaplar, açık bırakılan yönetim arayüzleri, üretimde
        DEBUG seviyesi log, gereksiz açık portlar ve aşırı geniş bulut
        izinleri.""",
        license=CC, url="https://owasp.org/Top10/A05_2021-Security_Misconfiguration/",
        tags=["yapılandırma", "log", "debug", "yönetim paneli"]),
    entry("owasp", "A06:2021", "Güncel olmayan ve açık içeren bileşenler",
        """Bilinen açığı olan kütüphane, çalışma zamanı veya işletim sistemi
        kullanmak; bağımlılık envanterinin ve güncelleme sürecinin
        olmaması.""",
        license=CC, url="https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/",
        tags=["bağımlılık", "yama", "envanter"]),
    entry("owasp", "A07:2021", "Kimlik doğrulama hataları",
        """Kaba kuvvete açık giriş, deneme sınırı olmayan OTP, zayıf parola
        politikası, oturum sabitleme, uzun ömürlü ve iptal edilemeyen
        token'lar.""",
        license=CC, url="https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/",
        tags=["kimlik doğrulama", "otp", "oturum", "mfa"]),
    entry("owasp", "A08:2021", "Yazılım ve veri bütünlüğü hataları",
        """İmzası doğrulanmayan güncellemeler, güvenilmeyen kaynaktan gelen
        model veya eklenti dosyaları, güvensiz serileştirme, denetimsiz CI/CD
        hattı.""",
        license=CC, url="https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/",
        tags=["bütünlük", "ci/cd", "model", "imza"]),
    entry("owasp", "A09:2021", "Günlükleme ve izleme eksikliği",
        """Kritik olayların kaydedilmemesi, kayıtların merkezi olarak
        incelenmemesi, alarm üretilmemesi; saldırının fark edilmesini
        geciktirir.""",
        license=CC, url="https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/",
        tags=["log", "izleme", "alarm", "denetim izi"]),
    entry("owasp", "A10:2021", "Sunucu taraflı istek sahteciliği (SSRF)",
        """Sunucunun, kullanıcıdan gelen adrese istek yapması. Doğrulanmayan
        webhook/callback adresleri iç ağ servislerine ve bulut meta veri
        uçlarına erişime yol açar.""",
        license=CC, url="https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/",
        tags=["ssrf", "webhook", "callback", "iç ağ"]),
]

API_TOP10 = [
    entry("api_owasp", "API1:2023", "Nesne düzeyi yetkilendirme bozuklukları (BOLA)",
        """İstekteki nesne kimliği değiştirilerek başka bir müşterinin
        verisine erişilmesi. Her istekte nesnenin istek sahibine ait olduğu
        sunucu tarafında doğrulanmalıdır. Bankacılık API'lerinde en sık ve en
        kritik bulgudur.""",
        license=CC, url="https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/",
        tags=["api", "yetki", "bola", "idor", "hesap"]),
    entry("api_owasp", "API2:2023", "Bozuk kimlik doğrulama",
        """Zayıf token üretimi, süresi dolmayan token, deneme sınırı olmayan
        giriş ve OTP uçları, parola sıfırlama akışındaki zayıflıklar.""",
        license=CC, url="https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/",
        tags=["api", "kimlik doğrulama", "token", "otp"]),
    entry("api_owasp", "API3:2023", "Nesne özelliği düzeyinde yetkilendirme bozuklukları",
        """İstemcinin görmemesi gereken alanların yanıtta dönmesi (aşırı veri
        ifşası) veya değiştirmemesi gereken alanları gönderebilmesi (mass
        assignment).""",
        license=CC, url="https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/",
        tags=["api", "veri ifşası", "mass assignment"]),
    entry("api_owasp", "API4:2023", "Sınırsız kaynak tüketimi",
        """Hız sınırı, sayfalama sınırı veya kota olmaması. İstemciden alınan
        limit parametresi, pahalı üçüncü taraf sorgularını tetikleyen uçlar ve
        toplu veri çekme bu başlıktadır.""",
        license=CC, url="https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/",
        tags=["api", "hız sınırı", "kota", "dos", "sayfalama"]),
    entry("api_owasp", "API5:2023", "Fonksiyon düzeyi yetkilendirme bozuklukları",
        """Yönetici işlevlerine normal kullanıcının erişebilmesi; rol
        kontrolünün yalnızca arayüzde yapılması.""",
        license=CC, url="https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/",
        tags=["api", "yetki", "rbac", "yönetim paneli"]),
    entry("api_owasp", "API6:2023", "Hassas iş akışlarına sınırsız erişim",
        """Otomasyona açık iş akışları: toplu başvuru oluşturma, kampanya
        suistimali, rezervasyon doldurma. Maliyet ve hizmet kalitesi
        etkilenir.""",
        license=CC, url="https://owasp.org/API-Security/editions/2023/en/0xa6-unrestricted-access-to-sensitive-business-flows/",
        tags=["api", "iş mantığı", "otomasyon", "kampanya"]),
    entry("api_owasp", "API7:2023", "Sunucu taraflı istek sahteciliği",
        """API'nin kullanıcıdan gelen URL'ye istek yapması; iç ağ ve bulut
        meta veri servislerine erişim riski.""",
        license=CC, url="https://owasp.org/API-Security/editions/2023/en/0xa7-server-side-request-forgery/",
        tags=["api", "ssrf", "webhook", "callback"]),
    entry("api_owasp", "API8:2023", "Güvenlik yanlış yapılandırması",
        """Eksik TLS, gereksiz HTTP metotları, hatalı CORS, ayrıntılı hata
        mesajları, üretimde açık hata ayıklama uçları.""",
        license=CC, url="https://owasp.org/API-Security/editions/2023/en/0xa8-security-misconfiguration/",
        tags=["api", "yapılandırma", "cors", "tls"]),
    entry("api_owasp", "API9:2023", "Uygun olmayan envanter yönetimi",
        """Eski sürüm API'lerin açık kalması, belgelenmemiş uçlar, gerçek veri
        içeren sandbox ortamları.""",
        license=CC, url="https://owasp.org/API-Security/editions/2023/en/0xa9-improper-inventory-management/",
        tags=["api", "envanter", "sandbox", "sürüm"]),
    entry("api_owasp", "API10:2023", "API'lerin güvensiz tüketimi",
        """Üçüncü taraf API'den gelen yanıta körü körüne güvenmek; imzasız
        webhook'ları kabul etmek, yönlendirmeleri doğrulamamak.""",
        license=CC, url="https://owasp.org/API-Security/editions/2023/en/0xaa-unsafe-consumption-of-apis/",
        tags=["api", "üçüncü taraf", "webhook", "imza"]),
]

MASVS = [
    entry("masvs", "MASVS-STORAGE", "Mobil: yerel veri saklama",
        """Hassas verinin cihazda şifresiz saklanmaması, yedeklere ve ekran
        görüntülerine sızmaması, anahtarların güvenli donanım deposunda
        tutulması.""",
        license=CC, url="https://mas.owasp.org/MASVS/05-MASVS-STORAGE/",
        tags=["mobil", "saklama", "keystore"]),
    entry("masvs", "MASVS-CRYPTO", "Mobil: kriptografi",
        """Standart algoritmaların doğru kullanımı, anahtarların uygulama
        içinde gömülü olmaması.""",
        license=CC, url="https://mas.owasp.org/MASVS/06-MASVS-CRYPTO/",
        tags=["mobil", "şifreleme", "anahtar"]),
    entry("masvs", "MASVS-AUTH", "Mobil: kimlik doğrulama ve yetkilendirme",
        """Biyometrinin yalnızca kolaylık katmanı olması, oturumun sunucuda
        doğrulanması, cihaz bağlama.""",
        license=CC, url="https://mas.owasp.org/MASVS/07-MASVS-AUTH/",
        tags=["mobil", "biyometri", "oturum", "cihaz bağlama"]),
    entry("masvs", "MASVS-NETWORK", "Mobil: ağ iletişimi",
        """TLS zorunluluğu ve sertifika sabitleme (certificate pinning); araya
        girme saldırılarına karşı temel önlem.""",
        license=CC, url="https://mas.owasp.org/MASVS/08-MASVS-NETWORK/",
        tags=["mobil", "tls", "sertifika sabitleme", "mitm"]),
    entry("masvs", "MASVS-PLATFORM", "Mobil: platform etkileşimi",
        """Derin bağlantıların, ekran paylaşımının, pano ve IPC kanallarının
        güvenli kullanımı.""",
        license=CC, url="https://mas.owasp.org/MASVS/09-MASVS-PLATFORM/",
        tags=["mobil", "deep link", "ipc"]),
    entry("masvs", "MASVS-CODE", "Mobil: kod kalitesi ve güncelleme",
        """Bağımlılıkların güncelliği, zorunlu sürüm güncelleme mekanizması,
        hata ayıklama kodunun üretimde kalmaması.""",
        license=CC, url="https://mas.owasp.org/MASVS/10-MASVS-CODE/",
        tags=["mobil", "bağımlılık", "güncelleme"]),
    entry("masvs", "MASVS-RESILIENCE", "Mobil: dayanıklılık",
        """Root/jailbreak tespiti, kod karartma, kurcalama tespiti; tek
        başına güvenlik sağlamaz ama saldırı maliyetini yükseltir.""",
        license=CC, url="https://mas.owasp.org/MASVS/11-MASVS-RESILIENCE/",
        tags=["mobil", "root", "jailbreak", "obfuscation"]),
    entry("masvs", "MASVS-PRIVACY", "Mobil: gizlilik",
        """Gereksiz izin istenmemesi, veri toplamanın asgari ve şeffaf
        olması.""",
        license=CC, url="https://mas.owasp.org/MASVS/12-MASVS-PRIVACY/",
        tags=["mobil", "gizlilik", "izin"]),
]

LLM_TOP10 = [
    entry("owasp_llm", "LLM01", "İstem enjeksiyonu (prompt injection)",
        """Modele verilen güvenilmez içeriğin talimat gibi işlenmesi. Dokümandan,
        web sayfasından veya kullanıcıdan gelen metin asla talimat olarak
        verilmemeli, açıkça sınırlandırılmış veri bloğunda taşınmalıdır.""",
        license=CC, url="https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
        tags=["llm", "prompt injection", "yapay zekâ"]),
    entry("owasp_llm", "LLM02", "Hassas bilginin ifşası",
        """Modele gönderilen verinin sağlayıcı tarafında saklanması veya model
        yanıtında başka kullanıcıya sızması. Ücretsiz katmanlarda gerçek
        müşteri verisi kullanılmamalıdır.""",
        license=CC, url="https://genai.owasp.org/llmrisk/llm02-sensitive-information-disclosure/",
        tags=["llm", "veri sızması", "gizlilik"]),
    entry("owasp_llm", "LLM03", "Tedarik zinciri riskleri",
        """Güvenilmeyen model dosyaları, eklentiler ve veri kümeleri; imza ve
        sürüm kontrolü olmadan kullanılan modeller.""",
        license=CC, url="https://genai.owasp.org/llmrisk/llm03-supply-chain/",
        tags=["llm", "model", "tedarik zinciri", "imza"]),
    entry("owasp_llm", "LLM04", "Veri ve model zehirlenmesi",
        """Eğitim veya ince ayar verisine kötü niyetli kayıt eklenmesi; model
        dosyasının paylaşımlı bir klasörde değiştirilebilmesi.""",
        license=CC, url="https://genai.owasp.org/llmrisk/llm04-data-and-model-poisoning/",
        tags=["llm", "model zehirleme", "eğitim verisi"]),
    entry("owasp_llm", "LLM05", "Hatalı çıktı işleme",
        """Model çıktısının doğrulanmadan koda, sorguya veya komuta
        verilmesi. Çıktı daima şema ile doğrulanmalı ve kod kararı
        vermelidir.""",
        license=CC, url="https://genai.owasp.org/llmrisk/llm05-improper-output-handling/",
        tags=["llm", "çıktı doğrulama", "şema"]),
    entry("owasp_llm", "LLM06", "Aşırı yetkilendirme",
        """Modelin veya ajanın gereğinden fazla yetkiyle sistemlere
        erişmesi; LLM'in veritabanına doğrudan yazabilmesi gibi.""",
        license=CC, url="https://genai.owasp.org/llmrisk/llm06-excessive-agency/",
        tags=["llm", "yetki", "ajan"]),
    entry("owasp_llm", "LLM07", "Sistem istemi sızıntısı",
        """Sistem isteminin kullanıcıya açılması ve içindeki iş kurallarının
        ya da sırların öğrenilmesi.""",
        license=CC, url="https://genai.owasp.org/llmrisk/llm07-system-prompt-leakage/",
        tags=["llm", "istem", "sızıntı"]),
    entry("owasp_llm", "LLM08", "Vektör ve gömme zayıflıkları",
        """RAG bilgi tabanına yetkisiz kayıt eklenmesi veya yetki filtresi
        olmadan arama yapılması; kullanıcının görmemesi gereken belgelerin
        yanıta girmesi.""",
        license=CC, url="https://genai.owasp.org/llmrisk/llm08-vector-and-embedding-weaknesses/",
        tags=["llm", "rag", "vektör", "yetki filtresi"]),
    entry("owasp_llm", "LLM09", "Yanlış bilgi (halüsinasyon)",
        """Modelin uydurduğu kimlik, kaynak veya madde numarası. Her kimlik
        bilgi tabanında doğrulanmalı, doğrulanamayan kimlik reddedilmelidir.""",
        license=CC, url="https://genai.owasp.org/llmrisk/llm09-misinformation/",
        tags=["llm", "halüsinasyon", "kaynak doğrulama"]),
    entry("owasp_llm", "LLM10", "Sınırsız tüketim",
        """Kota ve maliyet kontrolü olmadan model çağrısı yapılması; kota
        tükendiğinde sistemin çalışamaz hâle gelmesi.""",
        license=CC, url="https://genai.owasp.org/llmrisk/llm10-unbounded-consumption/",
        tags=["llm", "kota", "maliyet"]),
]

ENTRIES = TOP10 + API_TOP10 + MASVS + LLM_TOP10
