// Labels for threat attributes. Codes stay English; everything shown is Turkish.

export const STRIDE_LABELS: Record<string, string> = {
  S: "S · Kimlik taklidi",
  T: "T · Veri değiştirme",
  R: "R · İnkâr",
  I: "I · Bilgi sızması",
  D: "D · Hizmet kesintisi",
  E: "E · Yetki yükseltme",
};

export const STRIDE_SHORT: Record<string, string> = {
  S: "Kimlik taklidi",
  T: "Veri değiştirme",
  R: "İnkâr",
  I: "Bilgi sızması",
  D: "Hizmet kesintisi",
  E: "Yetki yükseltme",
};

export const SOURCE_LABELS: Record<string, string> = {
  rule: "Kural kataloğu",
  llm: "AI önerisi",
  merged: "Kural + AI",
};

export const REVIEW_LABELS: Record<string, string> = {
  pending: "Bekliyor",
  accepted: "Kabul",
  rejected: "Reddedildi",
  false_positive: "Yanlış pozitif",
  edited: "Düzenlendi",
};

export const VALIDATION_LABELS: Record<string, string> = {
  not_run: "Çalışmadı",
  ok: "Geçti",
  flagged: "İşaretli",
};
