#!/usr/bin/env python3
"""
Busca imagem em banco de imagens (Pexels) para ilustrar seções do artigo.

Licença Pexels: uso livre, sem atribuição obrigatória (creditamos por boa prática).
Falha graciosa: sem chave ou sem resultado, retorna None — o artigo é gerado
mesmo assim (só sem aquela imagem inline).

Requer (opcional): PEXELS_API_KEY  (chave grátis em pexels.com/api)

Uso (import):
    from buscar_imagem import buscar
    info = buscar("whatsapp business phone", "/caminho/img-1.jpg")
    # info = {"path","credit","credit_url","alt","origem"} ou None
"""
import os, sys, json, urllib.request, urllib.parse

PEXELS = "https://api.pexels.com/v1/search"
# User-Agent normal: a Pexels (Cloudflare) bloqueia o UA padrão do urllib com 403.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def buscar(query, out_path, orientation="landscape"):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    try:
        qs = urllib.parse.urlencode({
            "query": query, "per_page": 1,
            "orientation": orientation, "size": "large",
        })
        req = urllib.request.Request(f"{PEXELS}?{qs}",
                                     headers={"Authorization": key, "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        photos = data.get("photos", [])
        if not photos:
            return None
        ph = photos[0]
        src = ph["src"].get("large2x") or ph["src"].get("large") or ph["src"]["original"]
        img_req = urllib.request.Request(src, headers={"User-Agent": UA})
        with urllib.request.urlopen(img_req, timeout=30) as r:
            open(out_path, "wb").write(r.read())
        return {
            "path": out_path,
            "credit": ph.get("photographer", ""),
            "credit_url": ph.get("photographer_url", ""),
            "alt": ph.get("alt") or query,
            "origem": "Pexels",
        }
    except Exception as e:
        print(f"  aviso: busca de imagem falhou ({query}): {e}", file=sys.stderr)
        return None


def main():
    if len(sys.argv) < 3:
        print('Uso: python3 buscar_imagem.py "query" saida.jpg')
        return 1
    info = buscar(sys.argv[1], sys.argv[2])
    print(json.dumps(info, ensure_ascii=False) if info else "sem imagem (sem chave ou sem resultado)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
