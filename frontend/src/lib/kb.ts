// Labels for knowledge base sources and retrieval engines.

export const SOURCE_LABELS: Record<string, string> = {
  stride: "STRIDE",
  linddun: "LINDDUN",
  owasp: "OWASP Top 10",
  api_owasp: "OWASP API Top 10",
  masvs: "OWASP MASVS",
  owasp_llm: "OWASP LLM Top 10",
  cwe: "CWE",
  capec: "CAPEC",
  attack: "MITRE ATT&CK",
  attack_mobile: "MITRE ATT&CK Mobile",
  iso27001: "ISO/IEC 27001:2022",
  nist80053: "NIST SP 800-53",
  asvs: "OWASP ASVS",
  tr_regulation: "Türkiye mevzuatı",
};

export const MATCH_LABELS: Record<string, string> = {
  identifier: "Tam kimlik eşleşmesi",
  fulltext: "Anahtar kelime",
  vector: "Anlamsal benzerlik",
};

export function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}
