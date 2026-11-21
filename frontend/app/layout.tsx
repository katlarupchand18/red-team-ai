import type { Metadata } from "next";
import React from "react";
import "./style.css";
export const metadata: Metadata = { title: "RED TEAM AI | Prompt Safety Tester", description: "Authorized prompt safety evaluation" };
export default function Layout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html>; }
