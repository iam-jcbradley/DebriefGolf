import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import { CurrentUserProvider } from "@/lib/current-user";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Editorial serif for headlines and stat callouts — the "club moments".
// Optical-size axis dialed toward its display cut so it reads warm and a
// little characterful at large sizes rather than book-text neutral.
const fraunces = Fraunces({
  variable: "--font-serif",
  subsets: ["latin"],
  axes: ["opsz", "SOFT"],
});

export const metadata: Metadata = {
  title: "Debrief Golf",
  description: "Arccos-grade post-round diagnostics for the Garmin Golf ecosystem.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} antialiased`}
      >
        <CurrentUserProvider>{children}</CurrentUserProvider>
      </body>
    </html>
  );
}
