# Beklenen bulgular

`beklenen_bulgular.md` uzman gözüyle elle yazılmış listedir ve insan içindir.
Bu klasördeki `*.yaml` dosyaları aynı listenin makine okunur hâlidir;
`backend/scripts/eval.py` bunları "doğru cevap seti" olarak kullanır.

Her madde bir veya daha fazla kural kimliğine (`rules`) eşlenir. Bir bulgu,
eşlendiği kurallardan **en az biri** tetiklendiyse yakalanmış sayılır.
`keywords` alanı, kural kataloğu dışında (örneğin LLM tarafından) üretilmiş
bir tehdidin başlığında aranır; kural eşleşmesi yoksa ikinci bir şans verir.

Bu ölçüm **yalnızca model kalitesini** gösterir: kural kataloğunun ve
istemlerin bu üç dokümanda ne kadarını yakaladığını söyler. Güvenlik
etkinliğinin kanıtı değildir.
