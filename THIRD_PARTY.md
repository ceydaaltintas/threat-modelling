# Ucuncu taraf bilesenler ve veri kaynaklari

Bu dosya, projede kullanilan ucuncu taraf yazilim paketlerini ve veri
kaynaklarini lisanslariyla birlikte listeler. Yeni bir paket veya veri kaynagi
eklendiginde bu dosya guncellenir.

## Altyapi (konteyner imajlari)

| Bilesen | Surum | Lisans | Not |
|---|---|---|---|
| PostgreSQL | 16 | PostgreSQL License (BSD benzeri) | `pgvector/pgvector:pg16` imajiyla gelir |
| pgvector | 0.7+ | PostgreSQL License | Vektor benzerlik aramasi |
| Python | 3.12 (slim) | PSF License | Backend calisma ortami |
| Node.js | 20 (alpine) | MIT | Frontend calisma ortami |

## Backend (Python)

| Paket | Lisans | Kullanim amaci |
|---|---|---|
| fastapi | MIT | REST + SSE uclari |
| uvicorn | BSD-3-Clause | ASGI sunucusu |
| sqlalchemy | MIT | ORM |
| alembic | MIT | Veritabani migration |
| psycopg (3) | LGPL-3.0 | PostgreSQL surucusu |
| pydantic / pydantic-settings | MIT | Sema dogrulama, ayarlar |
| pgvector (python) | PostgreSQL License | SQLAlchemy vektor tipi |
| sse-starlette | BSD-3-Clause | Server-Sent Events |
| python-multipart | Apache-2.0 | Dosya yukleme |
| httpx | BSD-3-Clause | OpenAI uyumlu saglayici istemcisi, testler |
| pytest / pytest-asyncio | MIT | Testler |
| pymupdf (PyMuPDF) | **AGPL-3.0** | PDF metin cikarma ve sayfa goruntuleme |
| python-docx | MIT | DOCX okuma |
| google-genai | Apache-2.0 | Gemini yerel istemcisi |

**PyMuPDF uyarisi:** AGPL-3.0 lisanslidir. Bu demo kurum ici ve dagitilmayan
bir uygulama oldugu icin sorun degildir; urunlesme durumunda ya ticari lisans
alinmali ya da pdfplumber/pypdfium2 gibi bir alternatife gecilmelidir.

Asama 2 ve sonrasinda eklenecek paketler (fastembed, openpyxl, WeasyPrint vb.)
eklendikleri asamada bu tabloya islenecektir.

## Frontend (JavaScript / TypeScript)

| Paket | Lisans | Kullanim amaci |
|---|---|---|
| next | MIT | Uygulama cercevesi (App Router) |
| react / react-dom | MIT | Arayuz kutuphanesi |
| typescript | Apache-2.0 | Tip sistemi |
| tailwindcss | MIT | Stil |
| lucide-react | ISC | Ikonlar |
| class-variance-authority | Apache-2.0 | Bilesen varyantlari |
| clsx / tailwind-merge | MIT | Sinif birlestirme |
| shadcn/ui desenleri | MIT | Bilesenler projeye kopyalanir (paket bagimliligi degil) |

Asama 1-4'te eklenecek: `@tanstack/react-table` (MIT), `recharts` (MIT),
`reactflow` / `@xyflow/react` (MIT).

## Bilgi tabani veri kaynaklari (Asama 2)

Bilgi tabanina **telifli standartlarin tam metni konulmaz.** Yalnizca madde
kimligi, baslik ve projede yazilmis kisa ozet saklanir.

| Kaynak | Durum | Not |
|---|---|---|
| MITRE ATT&CK | Apache-2.0 (atif zorunlu) | Atif arayuzde Bilgi Tabani ekraninda gosterilir |
| MITRE CWE / CAPEC | Serbest kullanim, atif zorunlu | Yaygin alt kume alinir |
| OWASP Top 10, API Top 10, MASVS, LLM Top 10 | CC BY-SA 4.0 | Yalnizca kimlik + kendi ozetimiz + baglanti |
| NIST SP 800-53 | Kamu malı (ABD) | Kimlik + kisa ozet |
| ISO/IEC 27001:2022 Ek A | **Telifli** | Yalnizca madde kimligi + kendi kisa ozetimiz; tam metin YOK |
| PCI DSS | **Telifli** | Yalnizca madde kimligi; tam metin YOK |
| BDDK yonetmelikleri, KVKK | Mevzuat | Yalnizca baslik + baglanti duzeyinde kunye; madde eslemesi `verification: "needed"` |
