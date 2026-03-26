"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Building2,
  FileText,
  Clock,
  ShieldCheck,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/entities", label: "Entidades", icon: Building2 },
  { href: "/documents", label: "Normas", icon: FileText },
  { href: "/runs", label: "Historial de Runs", icon: Clock },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <ShieldCheck size={20} style={{ color: "#3b82f6" }} />
          <h1>ReguTrack</h1>
        </div>
        <p>Monitor Normativo Colombia</p>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`nav-item ${path === href ? "active" : ""}`}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div>🕐 06:00 AM · América/Bogotá</div>
        <div style={{ marginTop: 4 }}>v1.0 · ACP IT</div>
      </div>
    </aside>
  );
}
