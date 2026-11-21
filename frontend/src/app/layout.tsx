import type { Metadata } from "next";

import { AppShell } from "@/components/layout/app-shell";

import "./globals.css";

const productName =
  process.env.NEXT_PUBLIC_APP_NAME ?? "Tehdit Modelleme Platformu";

export const metadata: Metadata = {
  title: {
    default: productName,
    template: `%s · ${productName}`,
  },
  description:
    "Mimari dokümanlardan tehdit modeli üreten kurum içi demo platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
