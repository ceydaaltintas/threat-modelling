"use client";

import * as React from "react";

import { DisclaimerBar } from "@/components/layout/disclaimer-bar";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { MetaProvider } from "@/components/providers/meta-provider";
import { RoleProvider } from "@/components/providers/role-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { ToastProvider } from "@/components/ui/toast";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <MetaProvider>
        <RoleProvider>
          <ToastProvider>
            <div className="flex h-dvh overflow-hidden">
              <Sidebar />
              <div className="flex min-w-0 flex-1 flex-col">
                <Topbar />
                <DisclaimerBar />
                <main className="min-w-0 flex-1 overflow-y-auto px-5 py-6">
                  <div className="mx-auto w-full max-w-[1400px] space-y-6">
                    {children}
                  </div>
                </main>
              </div>
            </div>
          </ToastProvider>
        </RoleProvider>
      </MetaProvider>
    </ThemeProvider>
  );
}
