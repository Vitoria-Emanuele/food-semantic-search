import argparse
import json
from pathlib import Path

DATA_PATH = Path("data/dados_limpos.json")


def load_records(path: Path) -> list[dict]:
    """Carrega o JSON (lista de objetos) ou JSON Lines."""
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else list(data.values())
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def dish_name(record: dict) -> str:
    """Acha o campo do nome do prato (qualquer chave que contenha 'dish')."""
    for key, value in record.items():
        if "dish" in key.lower() and isinstance(value, str):
            return value
    return str(next(iter(record.values())))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("keywords", nargs="+",
                        help="palavras que o prato deve conter")
    parser.add_argument("--max", type=int, default=15,
                        help="máximo de resultados")
    args = parser.parse_args()

    records = load_records(DATA_PATH)
    words = [w.lower() for w in args.keywords]

    matches = [
        r for r in records
        if all(w in json.dumps(r, ensure_ascii=False).lower() for w in words)
    ]

    print(f"{len(matches)} prato(s) encontrado(s) com {words}\n")
    for record in matches[: args.max]:
        print(f"- {dish_name(record)}")
        for key, value in record.items():
            if isinstance(value, str) and "dish" not in key.lower() and len(value) < 160:
                print(f"    {key}: {value}")
        print()


if __name__ == "__main__":
    main()
