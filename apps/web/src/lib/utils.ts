import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPLN(amount: number): string {
  return new Intl.NumberFormat("pl-PL", { style: "currency", currency: "PLN", maximumFractionDigits: 0 }).format(amount);
}

export function formatNIP(nip: string): string {
  if (nip.length !== 10) return nip;
  return `${nip.slice(0, 3)}-${nip.slice(3, 6)}-${nip.slice(6, 8)}-${nip.slice(8, 10)}`;
}

export function riskBandColor(band: string): string {
  const map: Record<string, string> = { A: "#22c55e", B: "#3b82f6", C: "#f59e0b", D: "#ef4444" };
  return map[band] || "#94a3b8";
}

export function riskBandLabel(band: string): string {
  const map: Record<string, string> = {
    A: "Niskie ryzyko",
    B: "Umiarkowane ryzyko",
    C: "Podwyższone ryzyko",
    D: "Wysokie ryzyko",
  };
  return map[band] || "Nieznane";
}
