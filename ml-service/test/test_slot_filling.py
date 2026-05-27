from pathlib import Path
import sys

ML_SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ML_SERVICE_DIR))

from ml_service import RuBertSlotFillingService

def main() -> None:
    model_path = ML_SERVICE_DIR / "models" / "rubert-slot-filling"
    service = RuBertSlotFillingService(model_path)

    text = [
        "Передай Алану Султангарееву, что он молодец",
        "Алан Султангареев, настрой телегу и всякие бэкенд штучки и зайди на пм-пу посел 18.00",
        "Передай Алану Султангарееву, что он должен поговорить с Сашей Романченко по поводу закрытия таски",
        ]
    
    for i in range(len(text)):
        result = service.extract(text[i])

        print("Text:", text[i])
        print("Recipient:", result.recipient)
        print("Message:", result.message)


if __name__ == "__main__":
    main()
