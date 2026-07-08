import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SEO 指挥中心",
  description: "igoriptv2.com SEO/GEO 指挥中心观测大屏",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full bg-[#080b12] text-[#edf4ff]">{children}</body>
    </html>
  );
}
