"""Utilitários do nicho político: UFs, formatação BR, carga dos JSON oficiais."""
import datetime as dt, json
from pathlib import Path
UF = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
      "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
      "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins"}
PREP = {"AC": "do", "AL": "de", "AP": "do", "AM": "do", "BA": "da", "CE": "do", "DF": "do", "ES": "do", "GO": "de", "MA": "do", "MT": "de", "MS": "de", "MG": "de", "PA": "do", "PB": "da", "PR": "do",
        "PE": "de", "PI": "do", "RJ": "do", "RN": "do", "RS": "do", "RO": "de", "RR": "de", "SC": "de", "SP": "de", "SE": "de", "TO": "do"}
MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
def brl(v): return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def brl0(v):
    if v >= 1e6: return "R$ " + f"{v / 1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + " mi"
    return "R$ " + f"{v:,.0f}".replace(",", ".")
def num(v): return f"{v:,}".replace(",", ".")
def pct(a, b): return f"{100 * a / b:.1f}".replace(".", ",") + "%" if b else "0%"
def data_br(s):
    try: return dt.date.fromisoformat(str(s)[:10]).strftime("%d/%m/%Y")
    except Exception: return ""
def idade(s, hoje=None):
    try:
        n = dt.date.fromisoformat(str(s)[:10]); h = hoje or dt.date.today()
        return h.year - n.year - ((h.month, h.day) < (n.month, n.day))
    except Exception: return None
def load(S, nome): return json.loads((S.ROOT / "data" / nome).read_text(encoding="utf-8"))
